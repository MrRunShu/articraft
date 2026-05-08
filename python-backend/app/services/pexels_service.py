import logging
from typing import Optional

import httpx

from app.constants.article import ArticleConstant
from app.models.enums import ImageMethodEnum

logger = logging.getLogger(__name__)


class PexelsService:
    def __init__(self):
        # Pexels API Key 暂未配置，搜索会直接走降级逻辑
        self._api_key: Optional[str] = None
        self._method = ImageMethodEnum.PICSUM
        try:
            from app.config import settings
            if hasattr(settings, "pexels_api_key") and settings.pexels_api_key:
                self._api_key = settings.pexels_api_key
                self._method = ImageMethodEnum.PEXELS
        except Exception:
            pass

    async def search_image(self, keywords: str) -> Optional[str]:
        """根据关键词搜索图片，Pexels 未配置时直接返回 None 触发降级"""
        if not self._api_key:
            return None
        try:
            url = (
                f"{ArticleConstant.PEXELS_API_URL}"
                f"?query={keywords}"
                f"&per_page={ArticleConstant.PEXELS_PER_PAGE}"
                f"&orientation={ArticleConstant.PEXELS_ORIENTATION_LANDSCAPE}"
            )
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers={"Authorization": self._api_key})
            if response.status_code != 200:
                return None
            photos = response.json().get("photos", [])
            if not photos:
                return None
            return photos[0].get("src", {}).get("large")
        except Exception as e:
            logger.error(f"Pexels API 调用异常: {e}")
            return None

    def get_fallback_image(self, position: int) -> str:
        """Picsum 随机图片（降级兜底）"""
        return ArticleConstant.PICSUM_URL_TEMPLATE.format(position * 100)

    def get_method(self) -> ImageMethodEnum:
        return self._method
