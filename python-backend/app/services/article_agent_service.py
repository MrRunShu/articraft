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
    TitleResult,
)
from app.services.cos_service import CosService
from app.services.pexels_service import PexelsService

logger = logging.getLogger(__name__)


class ArticleAgentService:
    def __init__(self):
        # 当前使用 DeepSeek
        # 切换到 DashScope：api_key=settings.dashscope_api_key,
        #                   base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
        self.model = settings.deepseek_model
        self.pexels_service = PexelsService()
        self.cos_service = CosService()

    async def execute_article_generation(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """执行完整的5智能体文章生成流程"""
        try:
            await self.agent1_generate_title(state)
            stream_handler(SseMessageTypeEnum.AGENT1_COMPLETE.value)

            await self.agent2_generate_outline(state, stream_handler)
            stream_handler(SseMessageTypeEnum.AGENT2_COMPLETE.value)

            await self.agent3_generate_content(state, stream_handler)
            stream_handler(SseMessageTypeEnum.AGENT3_COMPLETE.value)

            await self.agent4_analyze_image_requirements(state)
            stream_handler(SseMessageTypeEnum.AGENT4_COMPLETE.value)

            await self.agent5_generate_images(state, stream_handler)
            stream_handler(SseMessageTypeEnum.AGENT5_COMPLETE.value)

            self.merge_images_into_content(state)
            stream_handler(SseMessageTypeEnum.MERGE_COMPLETE.value)
        except Exception as e:
            raise RuntimeError(f"文章生成失败: {str(e)}")

    async def agent1_generate_title(self, state: ArticleState):
        """智能体1：生成标题（非流式）"""
        prompt = PromptConstant.AGENT1_TITLE_PROMPT.replace("{topic}", state.topic)
        content = await self._call_llm(prompt)
        title_data = self._parse_json_response(content, "标题")
        state.title = TitleResult(**title_data)

    async def agent2_generate_outline(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体2：生成大纲（流式输出）"""
        prompt = (
            PromptConstant.AGENT2_OUTLINE_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
        )
        content = await self._call_llm_with_streaming(
            prompt, stream_handler, SseMessageTypeEnum.AGENT2_STREAMING
        )
        outline_data = self._parse_json_response(content, "大纲")
        state.outline = OutlineResult(
            sections=[OutlineSection(**s) for s in outline_data["sections"]]
        )

    async def agent3_generate_content(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体3：生成正文（流式输出）"""
        outline_text = json.dumps(
            [s.model_dump() for s in state.outline.sections], ensure_ascii=False
        )
        prompt = (
            PromptConstant.AGENT3_CONTENT_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{outline}", outline_text)
        )
        content = await self._call_llm_with_streaming(
            prompt, stream_handler, SseMessageTypeEnum.AGENT3_STREAMING
        )
        state.content = content

    async def agent4_analyze_image_requirements(self, state: ArticleState):
        """智能体4：分析配图需求（非流式）"""
        prompt = (
            PromptConstant.AGENT4_IMAGE_REQUIREMENTS_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{content}", state.content)
        )
        content = await self._call_llm(prompt)
        requirements_data = self._parse_json_response(content, "配图需求", is_list=True)
        state.image_requirements = [ImageRequirement(**r) for r in requirements_data]

    async def agent5_generate_images(
        self, state: ArticleState, stream_handler: Callable[[str], None]
    ):
        """智能体5：搜索配图（串行，Pexels降级Picsum）"""
        image_results: List[ImageResult] = []
        for req in state.image_requirements:
            image_url = await self.pexels_service.search_image(req.keywords)
            method = self.pexels_service.get_method()
            if image_url is None:
                image_url = self.pexels_service.get_fallback_image(req.position)
                method = ImageMethodEnum.PICSUM

            final_url = self.cos_service.use_direct_url(image_url)
            result = ImageResult(
                position=req.position,
                url=final_url,
                method=method.value,
                keywords=req.keywords,
                sectionTitle=req.section_title,
                description=f"{req.type} image for {req.section_title or 'cover'}",
            )
            image_results.append(result)

            msg = SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix() + result.model_dump_json(by_alias=True)
            stream_handler(msg)

        state.images = image_results

    def merge_images_into_content(self, state: ArticleState):
        """图文合成：在对应 ## 章节标题后插入配图"""
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
            if line.startswith("## "):
                section_title = line[3:].strip()
                if section_title in non_cover_images:
                    result_lines.append(f"\n![{section_title}]({non_cover_images[section_title]})\n")

        state.full_content = "\n".join(result_lines)

    async def _call_llm(self, prompt: str) -> str:
        """非流式调用"""
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
        """流式调用：逐块推送 + 拼接完整结果"""
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
        """解析大模型返回的 JSON，去掉可能的 markdown 代码块标记"""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        # 处理 LLM 偶尔返回 {{...}} / [[...]] 的情况
        cleaned = cleaned.strip()
        if cleaned.startswith("{{") and cleaned.endswith("}}"):
            cleaned = cleaned[1:-1]
        elif cleaned.startswith("[[") and cleaned.endswith("]]"):
            cleaned = cleaned[1:-1]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"{name}解析失败, content={content[:200]}, error={e}")
            raise RuntimeError(f"{name}解析失败: {str(e)}")
