import base64
import logging
from typing import Optional

from app.models.enums import ImageMethodEnum
from app.services.image.image_search_service import ImageData, ImageRequest, ImageSearchService

logger = logging.getLogger(__name__)


class NanoBananaService(ImageSearchService):
    """Gemini AI 生图服务（Nano Banana）"""

    def __init__(self):
        self._api_key: Optional[str] = None
        self._model: str = "gemini-2.0-flash-preview-image-generation"
        try:
            from app.config import settings
            if settings.nano_banana_api_key:
                self._api_key = settings.nano_banana_api_key
                self._model = settings.nano_banana_model
        except Exception:
            pass

    def get_method(self) -> ImageMethodEnum:
        return ImageMethodEnum.NANO_BANANA

    async def search(self, request: ImageRequest) -> Optional[ImageData]:
        if not self._api_key:
            return None
        try:
            import httpx
            prompt = f"Create a high-quality blog article illustration: {request.keywords}. Style: clean, modern, professional."
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]},
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error(f"Nano Banana API 错误: {response.status_code}")
                return None
            data = response.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            for part in parts:
                inline_data = part.get("inlineData", {})
                if inline_data.get("mimeType", "").startswith("image/"):
                    b64 = inline_data.get("data", "")
                    data_url = f"data:{inline_data['mimeType']};base64,{b64}"
                    return ImageData(url=data_url, method=ImageMethodEnum.NANO_BANANA)
            return None
        except Exception as e:
            logger.error(f"Nano Banana 生图异常: {e}")
            return None
