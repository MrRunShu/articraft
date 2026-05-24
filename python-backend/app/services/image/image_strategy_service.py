import logging
from typing import Optional

from app.models.enums import ImageMethodEnum
from app.services.diagram.emoji_pack_service import EmojiPackService
from app.services.diagram.iconify_service import IconifyService
from app.services.image.image_search_service import ImageData, ImageRequest, ImageSearchService
from app.services.diagram.mermaid_service import MermaidService
from app.services.image.nano_banana_service import NanoBananaService
from app.services.image.pexels_service import PexelsService
logger = logging.getLogger(__name__)


class ImageServiceStrategy:
    """配图策略选择器：根据配图方式路由到对应服务，失败自动降级"""

    def __init__(self):
        self._pexels = PexelsService()
        self._nano_banana = NanoBananaService()
        self._mermaid = MermaidService()
        self._iconify = IconifyService()
        self._emoji_pack = EmojiPackService()

        self._services: dict[ImageMethodEnum, ImageSearchService] = {
            ImageMethodEnum.PEXELS: self._pexels,
            ImageMethodEnum.NANO_BANANA: self._nano_banana,
            ImageMethodEnum.MERMAID: self._mermaid,
            ImageMethodEnum.ICONIFY: self._iconify,
            ImageMethodEnum.EMOJI_PACK: self._emoji_pack,
            # SVG_DIAGRAM 下架，路由到 Mermaid
            ImageMethodEnum.SVG_DIAGRAM: self._mermaid,
        }

    async def get_image(self, request: ImageRequest) -> ImageData:
        """按指定方式获取配图，失败时依次降级"""
        method = request.image_method
        service = self._services.get(method)

        if service:
            result = await service.search(request)
            if result:
                return result
            logger.warning(f"配图方式 {method.value} 获取失败，降级到 Pexels")

        # 降级链：Pexels → Picsum
        pexels_result = await self._pexels.search(request)
        if pexels_result:
            return pexels_result

        return self._pexels.get_fallback_image(request.position)
