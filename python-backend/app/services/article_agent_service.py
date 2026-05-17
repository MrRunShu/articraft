import json
import logging
from typing import Callable, List

from openai import AsyncOpenAI

from app.config import settings
from app.constants.prompt import PromptConstant
from app.models.enums import ImageMethodEnum, SseMessageTypeEnum
from app.schemas.article import (
    ArticleState,
    ImageRequirement,
    ImageResult,
    OutlineResult,
    OutlineSection,
    TitleOption,
    TitleResult,
)
from app.services.cos_service import CosService
from app.services.image_search_service import ImageRequest
from app.services.image_strategy_service import ImageServiceStrategy

logger = logging.getLogger(__name__)


class ArticleAgentService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
        self.model = settings.deepseek_model
        self.image_strategy = ImageServiceStrategy()
        self.cos_service = CosService()

    # ─── 三阶段入口 ───────────────────────────────────────────────────────────

    async def execute_phase1_generate_titles(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段1：生成标题方案（3-5个）"""
        try:
            logger.info("阶段1：开始生成标题方案, taskId=%s", state.task_id)
            await self.agent1_generate_title_options(state)
            stream_handler(SseMessageTypeEnum.AGENT1_COMPLETE.value)
            logger.info(
                "阶段1：标题方案生成成功, taskId=%s, count=%s",
                state.task_id,
                len(state.title_options or []),
            )
        except Exception as e:
            logger.error("阶段1失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"标题方案生成失败: {e}")

    async def execute_phase2_generate_outline(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段2：生成大纲（流式输出）"""
        try:
            logger.info("阶段2：开始生成大纲, taskId=%s", state.task_id)
            await self.agent2_generate_outline(state, stream_handler)
            stream_handler(SseMessageTypeEnum.AGENT2_COMPLETE.value)
            logger.info("阶段2：大纲生成成功, taskId=%s", state.task_id)
        except Exception as e:
            logger.error("阶段2失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"大纲生成失败: {e}")

    async def execute_phase3_generate_content(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段3：生成正文、配图和合并内容"""
        try:
            logger.info("阶段3：开始生成正文, taskId=%s", state.task_id)
            await self.agent3_generate_content(state, stream_handler)
            stream_handler(SseMessageTypeEnum.AGENT3_COMPLETE.value)

            logger.info("阶段3：开始分析配图需求, taskId=%s", state.task_id)
            await self.agent4_analyze_image_requirements(state)
            stream_handler(SseMessageTypeEnum.AGENT4_COMPLETE.value)

            logger.info("阶段3：开始生成配图, taskId=%s", state.task_id)
            await self.agent5_generate_images(state, stream_handler)
            stream_handler(SseMessageTypeEnum.AGENT5_COMPLETE.value)

            logger.info("阶段3：开始图文合成, taskId=%s", state.task_id)
            self.merge_images_into_content(state)
            stream_handler(SseMessageTypeEnum.MERGE_COMPLETE.value)
        except Exception as e:
            logger.error("阶段3失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"正文生成失败: {e}")

    # ─── 各智能体实现 ─────────────────────────────────────────────────────────

    async def agent1_generate_title_options(self, state: ArticleState):
        """智能体1：生成标题方案（3-5个）"""
        style_instruction = PromptConstant.get_style_instruction(state.style)
        prompt = (
            PromptConstant.AGENT1_TITLE_PROMPT
            .replace("{topic}", state.topic)
            .replace("{styleInstruction}", style_instruction)
        )
        content = await self._call_llm(prompt)
        title_options_data = self._parse_json_response(content, "标题方案", is_list=True)
        state.title_options = [TitleOption(**item) for item in title_options_data]
        logger.info("智能体1：标题方案生成成功, count=%s", len(state.title_options))

    async def agent2_generate_outline(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体2：生成大纲（流式输出，支持补充描述）"""
        description_section = ""
        if state.user_description and state.user_description.strip():
            description_section = PromptConstant.AGENT2_DESCRIPTION_SECTION.replace(
                "{userDescription}", state.user_description
            )

        style_instruction = PromptConstant.get_style_instruction(state.style)
        prompt = (
            PromptConstant.AGENT2_OUTLINE_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{descriptionSection}", description_section)
            .replace("{styleInstruction}", style_instruction)
        )
        content = await self._call_llm_with_streaming(
            prompt, stream_handler, SseMessageTypeEnum.AGENT2_STREAMING
        )
        logger.info("Agent2 LLM原文前500字: %s", content[:500])
        outline_data = self._parse_json_response(content, "大纲")
        sections = [OutlineSection(**s) for s in outline_data["sections"]]
        state.outline = OutlineResult(sections=sections)
        logger.info("智能体2：大纲生成成功, sections=%s", len(sections))

    async def agent3_generate_content(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体3：生成正文（流式输出，支持风格）"""
        outline_text = json.dumps(
            [s.model_dump() for s in state.outline.sections], ensure_ascii=False
        )
        style_instruction = PromptConstant.get_style_instruction(state.style)
        prompt = (
            PromptConstant.AGENT3_CONTENT_PROMPT
            .replace("{styleInstruction}", style_instruction)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{outline}", outline_text)
        )
        content = await self._call_llm_with_streaming(
            prompt, stream_handler, SseMessageTypeEnum.AGENT3_STREAMING
        )
        state.content = content

    async def agent4_analyze_image_requirements(self, state: ArticleState):
        """智能体4：分析配图需求并智能选择配图方式"""
        prompt = (
            PromptConstant.AGENT4_IMAGE_REQUIREMENTS_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{content}", state.content)
        )
        content = await self._call_llm(prompt)
        requirements_data = self._parse_json_response(content, "配图需求", is_list=True)

        # 过滤 enabledImageMethods
        enabled = state.enabled_image_methods
        filtered = []
        for r in requirements_data:
            method = r.get("imageMethod", "PEXELS")
            if enabled and method not in enabled:
                try:
                    method = next(m for m in enabled if m != "SVG_DIAGRAM")
                except StopIteration:
                    method = "PEXELS"
                r["imageMethod"] = method
            filtered.append(r)

        state.image_requirements = [ImageRequirement(**r) for r in filtered]

    async def agent5_generate_images(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体5：通过策略选择器获取配图"""
        image_results: List[ImageResult] = []
        for req in state.image_requirements:
            try:
                method_enum = ImageMethodEnum(req.image_method)
            except ValueError:
                method_enum = ImageMethodEnum.PEXELS

            image_request = ImageRequest(
                keywords=req.keywords,
                position=req.position,
                image_method=method_enum,
                section_title=req.section_title,
                description=f"{req.type} image for {req.section_title or 'cover'}",
            )
            image_data = await self.image_strategy.get_image(image_request)
            final_url = await self.cos_service.upload_async(image_data.url)

            result = ImageResult(
                position=req.position,
                url=final_url,
                method=image_data.method.value,
                keywords=req.keywords,
                sectionTitle=req.section_title,
                description=image_request.description,
            )
            image_results.append(result)

            msg = SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix() + result.model_dump_json(by_alias=True)
            stream_handler(msg)

        state.images = image_results

    async def ai_modify_outline(
        self,
        main_title: str,
        sub_title: str,
        current_outline: List[OutlineSection],
        modify_suggestion: str,
    ) -> List[OutlineSection]:
        """AI 修改大纲（同步返回修改结果）"""
        current_outline_json = json.dumps(
            [item.model_dump() for item in current_outline],
            ensure_ascii=False,
        )
        prompt = (
            PromptConstant.AI_MODIFY_OUTLINE_PROMPT
            .replace("{mainTitle}", main_title)
            .replace("{subTitle}", sub_title)
            .replace("{currentOutline}", current_outline_json)
            .replace("{modifySuggestion}", modify_suggestion)
        )
        content = await self._call_llm(prompt)
        outline_data = self._parse_json_response(content, "修改后的大纲")
        return [OutlineSection(**s) for s in outline_data["sections"]]

    def merge_images_into_content(self, state: ArticleState):
        """图文合成：在对应章节标题后插入配图（支持 ##/### 任意层级）"""
        if not state.images:
            state.full_content = state.content
            return

        non_cover_images = {
            img.section_title: img.url
            for img in state.images
            if img.position != 1
        }

        lines = state.content.split("\n")
        result_lines = []
        for line in lines:
            result_lines.append(line)
            stripped = line.lstrip("#")
            if stripped and line[0] == "#" and stripped[0] == " ":
                section_title = stripped[1:].strip()
                if section_title in non_cover_images:
                    result_lines.append(f"\n![{section_title}]({non_cover_images[section_title]})\n")

        state.full_content = "\n".join(result_lines)

    # ─── 内部工具 ─────────────────────────────────────────────────────────────

    def _get_style_prompt(self, style: str) -> str:
        return PromptConstant.get_style_instruction(style)

    async def _call_llm(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    async def _call_llm_with_streaming(
        self,
        prompt: str,
        stream_handler: Callable[[str], None],
        message_type: SseMessageTypeEnum,
    ) -> str:
        chunks = []
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                chunks.append(delta)
                stream_handler(message_type.get_streaming_prefix() + delta)
        return "".join(chunks)

    def _parse_json_response(self, content: str, name: str, is_list: bool = False):
        """解析大模型返回的 JSON，多层容错：代码块剥离 → 直接解析 → 正则提取 → 全文扫描"""
        import re

        def _try_loads(s: str):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return None

        # 1. 只替换单弯引号（U+2018/U+2019）；双弯引号先不动，避免把字符串内容中的强调词误转为 JSON 分隔符
        cleaned = content.strip()
        cleaned = cleaned.replace('‘', "'").replace('’', "'")

        # 2. 剥离 markdown 代码块（支持 ```json ... ``` 及嵌套前缀文字）
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
        if code_block:
            candidate = code_block.group(1).strip()
            result = _try_loads(candidate)
            if result is not None:
                return result

        # 3. 去掉首行非 JSON 前缀（LLM 可能先输出一句话再给 JSON）
        for line in cleaned.split('\n'):
            line = line.strip()
            if line.startswith(('{', '[')):
                result = _try_loads(line)
                if result is not None:
                    return result

        # 4. 去除双重花/方括号（Jinja 模板转义遗留）
        stripped = cleaned
        if stripped.startswith("{{") and stripped.endswith("}}"):
            stripped = stripped[1:-1]
        elif stripped.startswith("[[") and stripped.endswith("]]"):
            stripped = stripped[1:-1]
        result = _try_loads(stripped)
        if result is not None:
            return result

        # 5. 正则从全文中提取第一个完整 JSON 对象或数组
        for match in re.finditer(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned):
            result = _try_loads(match.group(1))
            if result is not None:
                return result

        # 6. 兜底：把双弯引号归一化为直引号后重试（应对 LLM 用弯引号作结构分隔符的情况）
        cleaned2 = cleaned.replace('“', '"').replace('”', '"')
        if cleaned2 != cleaned:
            for step in [cleaned2, cleaned2.split('\n')]:
                result = _try_loads(cleaned2)
                if result is not None:
                    return result
            for match in re.finditer(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned2):
                result = _try_loads(match.group(1))
                if result is not None:
                    return result

        logger.error("%s解析失败, content=%s", name, content[:500])
        raise RuntimeError(f"{name}解析失败: LLM 返回内容无法解析为 JSON")
