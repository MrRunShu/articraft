import base64
import logging
import re
from typing import Optional

from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageData, ImageRequest, ImageSearchService

logger = logging.getLogger(__name__)


class SvgDiagramService(ImageSearchService):
    """SVG 概念示意图服务（AI 生成矢量图）"""

    def get_method(self) -> ImageMethodEnum:
        return ImageMethodEnum.SVG_DIAGRAM

    async def search(self, request: ImageRequest) -> Optional[ImageData]:
        try:
            svg_content = await self._generate_svg(request.keywords, request.description)
            if not svg_content:
                return None
            b64 = base64.b64encode(svg_content.encode()).decode()
            data_url = f"data:image/svg+xml;base64,{b64}"
            return ImageData(url=data_url, method=ImageMethodEnum.SVG_DIAGRAM)
        except Exception as e:
            logger.error(f"SVG 生成异常: {e}")
            return None

    async def _generate_svg(self, keywords: str, description: str) -> Optional[str]:
        try:
            from app.config import settings
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")
            prompt = f"""请生成一个简洁的 SVG 概念示意图，用于说明以下内容：
关键词：{keywords}
说明：{description}

要求：
1. 只返回 SVG 代码，不要有其他内容
2. 宽度 800，高度 450
3. 使用蓝色系配色（#4096ff 主色）
4. 包含简单的图形和中文文字说明
5. 风格简洁、现代，适合插图使用
6. 不要使用外部字体或图片"""
            response = await client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content.strip()
            # 提取 SVG 代码
            if "<svg" in content:
                match = re.search(r"(<svg[\s\S]*?</svg>)", content)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            logger.error(f"SVG AI 生成失败: {e}")
            return None
