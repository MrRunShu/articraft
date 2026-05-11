import base64
import logging
from typing import Optional

import httpx

from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageData, ImageRequest, ImageSearchService

logger = logging.getLogger(__name__)


class IconifyService(ImageSearchService):
    """Iconify 图标库服务（免费公开 API）"""

    SEARCH_URL = "https://api.iconify.design/search"
    SVG_URL = "https://api.iconify.design/{prefix}/{name}.svg"

    def get_method(self) -> ImageMethodEnum:
        return ImageMethodEnum.ICONIFY

    async def search(self, request: ImageRequest) -> Optional[ImageData]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 搜索图标
                resp = await client.get(self.SEARCH_URL, params={"query": request.keywords, "limit": 1})
                if resp.status_code != 200:
                    return None
                icons = resp.json().get("icons", [])
                if not icons:
                    return None
                # 解析 prefix:name 格式
                icon_id = icons[0]
                if ":" not in icon_id:
                    return None
                prefix, name = icon_id.split(":", 1)
                # 获取 SVG
                svg_resp = await client.get(
                    self.SVG_URL.format(prefix=prefix, name=name),
                    params={"width": 400, "height": 400, "color": "%234096ff"},
                )
                if svg_resp.status_code != 200:
                    return None
                svg_content = svg_resp.text
                b64 = base64.b64encode(svg_content.encode()).decode()
                data_url = f"data:image/svg+xml;base64,{b64}"
                return ImageData(url=data_url, method=ImageMethodEnum.ICONIFY)
        except Exception as e:
            logger.error(f"Iconify 搜索异常: {e}")
            return None
