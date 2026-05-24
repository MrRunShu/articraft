import json
import logging
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Callable, List, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.constants.prompt import PromptConstant
from app.database import database
from app.models.enums import SseMessageTypeEnum
from app.schemas.article import (
    ArticleState,
    ImageRequirement,
    ImageResult,
    OutlineResult,
    OutlineSection,
    TitleOption,
    TitleResult,
)
from app.agent.orchestrator import ArticleAgentOrchestrator
from app.agent.parallel.image_generator import ParallelImageGenerator
from app.services.image.cos_service import CosService
from app.services.image.image_strategy_service import ImageServiceStrategy

logger = logging.getLogger(__name__)


class ArticleAgentService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
        self.model = settings.deepseek_model
        self.image_service_strategy = ImageServiceStrategy()
        self.cos_service = CosService()
        # 延迟导入避免循环依赖
        from app.services.analytics.agent_log_service import AgentLogService
        self.agent_log_service = AgentLogService(database)
        self.parallel_image_generator = ParallelImageGenerator(
            image_strategy=self.image_service_strategy,
            cos_service=self.cos_service,
            max_concurrency=settings.agent_image_max_concurrency,
            fail_fast=settings.agent_image_fail_fast,
        )
        self.orchestrator = ArticleAgentOrchestrator()

    # ─── 三阶段入口 ───────────────────────────────────────────────────────────

    async def execute_phase1_generate_titles(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段1：生成标题方案（委托给编排器）"""
        try:
            await self.orchestrator.execute_phase1(self, state, stream_handler)
        except Exception as e:
            logger.error("阶段1失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"标题方案生成失败: {e}") from e

    async def execute_phase2_generate_outline(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段2：生成大纲（委托给编排器）"""
        try:
            await self.orchestrator.execute_phase2(self, state, stream_handler)
        except Exception as e:
            logger.error("阶段2失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"大纲生成失败: {e}") from e

    async def execute_phase3_generate_content(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """阶段3：正文、配图、合并（委托给编排器）"""
        try:
            await self.orchestrator.execute_phase3(self, state, stream_handler)
        except Exception as e:
            logger.error("阶段3失败, taskId=%s, error=%s", state.task_id, e)
            raise RuntimeError(f"正文生成失败: {e}") from e

    # ─── 各智能体实现 ─────────────────────────────────────────────────────────

    async def agent1_generate_title_options(self, state: ArticleState):
        """智能体1：生成标题方案（3-5个）"""
        style_instruction = PromptConstant.get_style_instruction(state.style, state.language)
        prompt = (
            PromptConstant.get("AGENT1_TITLE_PROMPT", state.language)
            .replace("{topic}", state.topic)
            .replace("{styleInstruction}", style_instruction)
        )
        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent1_generate_titles",
            prompt=prompt,
            input_data={"topic": state.topic, "style": state.style},
        ) as log_data:
            content = await self._call_llm(prompt)
            title_options_data = self._parse_json_response(content, "标题方案", is_list=True)
            state.title_options = [TitleOption(**item) for item in title_options_data]
            log_data["outputData"] = self._safe_json_dumps({"optionsCount": len(state.title_options)})
            logger.info("智能体1：标题方案生成成功, count=%s", len(state.title_options))

    async def agent2_generate_outline(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体2：生成大纲（流式输出，支持补充描述）"""
        description_section = ""
        if state.user_description and state.user_description.strip():
            description_section = PromptConstant.get("AGENT2_DESCRIPTION_SECTION", state.language).replace(
                "{userDescription}", state.user_description
            )

        style_instruction = PromptConstant.get_style_instruction(state.style, state.language)
        prompt = (
            PromptConstant.get("AGENT2_OUTLINE_PROMPT", state.language)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{descriptionSection}", description_section)
            .replace("{styleInstruction}", style_instruction)
        )
        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent2_generate_outline",
            prompt=prompt,
            input_data={
                "mainTitle": state.title.main_title if state.title else None,
                "subTitle": state.title.sub_title if state.title else None,
                "hasUserDescription": bool(state.user_description and state.user_description.strip()),
            },
        ) as log_data:
            content = await self._call_llm_with_streaming(
                prompt, stream_handler, SseMessageTypeEnum.AGENT2_STREAMING
            )
            logger.info("Agent2 LLM原文前500字: %s", content[:500])
            outline_data = self._parse_json_response(content, "大纲")
            sections = [OutlineSection(**s) for s in outline_data["sections"]]
            state.outline = OutlineResult(sections=sections)
            log_data["outputData"] = self._safe_json_dumps({"sectionsCount": len(state.outline.sections)})
            logger.info("智能体2：大纲生成成功, sections=%s", len(sections))

    async def agent3_generate_content(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体3：生成正文（流式输出，支持风格）"""
        outline_text = json.dumps(
            [s.model_dump() for s in state.outline.sections], ensure_ascii=False
        )
        style_instruction = PromptConstant.get_style_instruction(state.style, state.language)
        prompt = (
            PromptConstant.get("AGENT3_CONTENT_PROMPT", state.language)
            .replace("{styleInstruction}", style_instruction)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{outline}", outline_text)
        )
        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent3_generate_content",
            prompt=prompt,
            input_data={
                "mainTitle": state.title.main_title if state.title else None,
                "sectionsCount": len(state.outline.sections) if state.outline else 0,
            },
        ) as log_data:
            content = await self._call_llm_with_streaming(
                prompt, stream_handler, SseMessageTypeEnum.AGENT3_STREAMING
            )
            state.content = content
            log_data["outputData"] = self._safe_json_dumps({"contentLength": len(content)})

    async def agent4_analyze_image_requirements(self, state: ArticleState):
        """智能体4：分析配图需求并智能选择配图方式"""
        prompt = (
            PromptConstant.get("AGENT4_IMAGE_REQUIREMENTS_PROMPT", state.language)
            .replace("{mainTitle}", state.title.main_title)
            .replace("{content}", state.content)
        )
        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent4_analyze_image_requirements",
            prompt=prompt,
            input_data={
                "mainTitle": state.title.main_title if state.title else None,
                "contentLength": len(state.content) if state.content else 0,
            },
        ) as log_data:
            content = await self._call_llm(prompt)
            requirements_data = self._parse_json_response(content, "配图需求", is_list=True)

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
            log_data["outputData"] = self._safe_json_dumps(
                {"requirementsCount": len(state.image_requirements)}
            )

    async def agent5_generate_images(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体5：并行生成配图（Day 8：使用 ParallelImageGenerator）"""
        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent5_generate_images",
            prompt=PromptConstant.AGENT5_IMAGE_EXECUTION_PROMPT,
            input_data={"requirementsCount": len(state.image_requirements or [])},
        ) as log_data:
            generated_triples = await self.parallel_image_generator.generate(
                state.image_requirements or []
            )
            image_results: List[ImageResult] = []

            for requirement, image_data, cos_url in generated_triples:
                result = ImageResult(
                    position=requirement.position,
                    url=cos_url,
                    method=image_data.method.value,
                    keywords=requirement.keywords,
                    sectionTitle=requirement.section_title,
                    description=f"{requirement.type} image for {requirement.section_title or 'cover'}",
                )
                image_results.append(result)

                msg = (
                    SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix()
                    + result.model_dump_json(by_alias=True)
                )
                stream_handler(msg)
                logger.info(
                    "智能体5：配图生成并上传成功, position=%s, method=%s, cosUrl=%s",
                    requirement.position,
                    image_data.method.value,
                    cos_url,
                )

            # 并行执行后按位置排序，确保顺序稳定
            state.images = sorted(image_results, key=lambda r: r.position)
            log_data["outputData"] = self._safe_json_dumps(
                {"imagesCount": len(state.images)}
            )
            logger.info("智能体5：所有配图生成完成, count=%s", len(state.images))

    async def ai_modify_outline(
        self,
        main_title: str,
        sub_title: str,
        current_outline: List[OutlineSection],
        modify_suggestion: str,
        task_id: Optional[str] = None,
        language: str = 'zh',   # 新增
    ) -> List[OutlineSection]:
        """AI 修改大纲（同步返回修改结果）"""
        current_outline_json = json.dumps(
            [item.model_dump() for item in current_outline],
            ensure_ascii=False,
        )
        prompt = (
            PromptConstant.get("AI_MODIFY_OUTLINE_PROMPT", language)
            .replace("{mainTitle}", main_title)
            .replace("{subTitle}", sub_title)
            .replace("{currentOutline}", current_outline_json)
            .replace("{modifySuggestion}", modify_suggestion)
        )
        async with self._agent_log_context(
            task_id=task_id,
            agent_name="ai_modify_outline",
            prompt=prompt,
            input_data={"mainTitle": main_title, "modifySuggestion": modify_suggestion},
        ) as log_data:
            content = await self._call_llm(prompt)
            outline_data = self._parse_json_response(content, "修改后的大纲")
            sections = [OutlineSection(**s) for s in outline_data["sections"]]
            log_data["outputData"] = self._safe_json_dumps({"sectionsCount": len(sections)})

        return sections

    def merge_images_into_content(self, state: ArticleState):
        """图文合成：在对应章节标题后插入配图（支持 ##/### 任意层级）"""
        with self._agent_log_context_sync(
            task_id=state.task_id,
            agent_name="agent6_merge_content",
            input_data={"imagesCount": len(state.images or [])},
        ) as log_data:
            if not state.images:
                state.full_content = state.content
                log_data["outputData"] = self._safe_json_dumps(
                    {"fullContentLength": len(state.content or "")}
                )
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
            log_data["outputData"] = self._safe_json_dumps(
                {"fullContentLength": len(state.full_content)}
            )

    # ─── 日志上下文管理器 ─────────────────────────────────────────

    @asynccontextmanager
    async def _agent_log_context(
        self,
        task_id: Optional[str],
        agent_name: str,
        prompt: Optional[str] = None,
        input_data: Optional[dict] = None,
    ):
        """异步智能体日志上下文：yield 前计时，yield 后提交日志（不阻塞主流程）"""
        start_time = datetime.now()
        log_data: dict = {
            "taskId": task_id or "unknown",
            "agentName": agent_name,
            "startTime": start_time,
            "status": "RUNNING",
            "prompt": prompt,
            "inputData": self._safe_json_dumps(input_data),
            "outputData": None,
            "errorMessage": None,
        }
        try:
            yield log_data
            log_data["status"] = "SUCCESS"
        except Exception as exc:
            log_data["status"] = "FAILED"
            log_data["errorMessage"] = str(exc)
            raise
        finally:
            end_time = datetime.now()
            log_data["endTime"] = end_time
            log_data["durationMs"] = int((end_time - start_time).total_seconds() * 1000)
            self.agent_log_service.save_log_async(log_data)

    @contextmanager
    def _agent_log_context_sync(
        self,
        task_id: Optional[str],
        agent_name: str,
        prompt: Optional[str] = None,
        input_data: Optional[dict] = None,
    ):
        """同步智能体日志上下文（用于 merge_images_into_content 等同步方法）"""
        start_time = datetime.now()
        log_data: dict = {
            "taskId": task_id or "unknown",
            "agentName": agent_name,
            "startTime": start_time,
            "status": "RUNNING",
            "prompt": prompt,
            "inputData": self._safe_json_dumps(input_data),
            "outputData": None,
            "errorMessage": None,
        }
        try:
            yield log_data
            log_data["status"] = "SUCCESS"
        except Exception as exc:
            log_data["status"] = "FAILED"
            log_data["errorMessage"] = str(exc)
            raise
        finally:
            end_time = datetime.now()
            log_data["endTime"] = end_time
            log_data["durationMs"] = int((end_time - start_time).total_seconds() * 1000)
            self.agent_log_service.save_log_async(log_data)

    @staticmethod
    def _safe_json_dumps(value: Optional[dict]) -> Optional[str]:
        if value is None:
            return None
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return None

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
