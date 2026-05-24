from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.models.enums import ImageMethodEnum


@dataclass
class ImageRequest:
    keywords: str
    position: int
    image_method: ImageMethodEnum
    section_title: str = ""
    description: str = ""


@dataclass
class ImageData:
    url: str
    method: ImageMethodEnum


class ImageSearchService(ABC):
    """配图服务抽象接口"""

    @abstractmethod
    def get_method(self) -> ImageMethodEnum:
        pass

    @abstractmethod
    async def search(self, request: ImageRequest) -> Optional[ImageData]:
        """搜索配图，失败返回 None 触发降级"""
        pass
