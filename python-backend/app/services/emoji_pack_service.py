import logging
from typing import Optional
from urllib.parse import quote

import httpx

from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageData, ImageRequest, ImageSearchService

logger = logging.getLogger(__name__)


class EmojiPackService(ImageSearchService):
    """表情包搜索服务（Bing 图片搜索）"""

    BING_SEARCH_URL = "https://www.bing.com/images/search"

    def get_method(self) -> ImageMethodEnum:
        return ImageMethodEnum.EMOJI_PACK

    async def search(self, request: ImageRequest) -> Optional[ImageData]:
        try:
            query = f"{request.keywords} meme funny"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(
                    self.BING_SEARCH_URL,
                    params={"q": query, "form": "HDRSC2", "first": "1"},
                    headers=headers,
                )
            if resp.status_code != 200:
                return None
            # 从 HTML 中提取第一张图片 URL
            import re
            # Bing 图片结果中的 murl 字段
            matches = re.findall(r'"murl":"(https?://[^"]+)"', resp.text)
            if not matches:
                return None
            image_url = matches[0]
            return ImageData(url=image_url, method=ImageMethodEnum.EMOJI_PACK)
        except Exception as e:
            logger.error(f"表情包搜索异常: {e}")
            return None
