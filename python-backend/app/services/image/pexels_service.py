import logging
from typing import Optional

import httpx

from app.constants.article import ArticleConstant
from app.models.enums import ImageMethodEnum
from app.services.image.image_search_service import ImageData, ImageRequest, ImageSearchService

logger = logging.getLogger(__name__)


class PexelsService(ImageSearchService):
    def __init__(self):
        self._api_key: Optional[str] = None
        try:
            from app.config import settings
            if settings.pexels_api_key:
                self._api_key = settings.pexels_api_key
        except Exception:
            pass

    def get_method(self) -> ImageMethodEnum:
        return ImageMethodEnum.PEXELS

    async def search(self, request: ImageRequest) -> Optional[ImageData]:
        if not self._api_key:
            return None
        try:
            url = (
                f"{ArticleConstant.PEXELS_API_URL}"
                f"?query={request.keywords}"
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
            image_url = photos[0].get("src", {}).get("large")
            if not image_url:
                return None
            return ImageData(url=image_url, method=ImageMethodEnum.PEXELS)
        except Exception as e:
            logger.error(f"Pexels API 调用异常: {e}")
            return None

    def get_fallback_image(self, position: int) -> ImageData:
        url = ArticleConstant.PICSUM_URL_TEMPLATE.format(position * 100)
        return ImageData(url=url, method=ImageMethodEnum.PICSUM)
