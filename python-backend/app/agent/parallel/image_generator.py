import asyncio
import logging
from typing import List, Tuple

from app.models.enums import ImageMethodEnum
from app.schemas.article import ImageRequirement
from app.services.cos_service import CosService
from app.services.image_search_service import ImageData, ImageRequest
from app.services.image_strategy_service import ImageServiceStrategy

logger = logging.getLogger(__name__)


class ParallelImageGenerator:
    """
    并行配图生成器。
    用 asyncio.Semaphore 控制最大并发数，asyncio.gather 同时提交所有任务。
    返回 (ImageRequirement, ImageData, cos_url) 三元组列表，顺序与输入一致（调用方负责排序）。
    """

    def __init__(
        self,
        image_strategy: ImageServiceStrategy,
        cos_service: CosService,
        max_concurrency: int,
        fail_fast: bool,
    ):
        self.image_strategy = image_strategy
        self.cos_service = cos_service
        self.max_concurrency = max(1, max_concurrency)
        self.fail_fast = fail_fast

    async def generate(
        self,
        requirements: List[ImageRequirement],
    ) -> List[Tuple[ImageRequirement, ImageData, str]]:
        """
        并行生成配图并上传至 COS。
        返回成功完成的 (requirement, image_data, cos_url) 列表。
        如果 fail_fast=True 且存在失败，抛出第一个异常；否则返回所有成功结果。
        """
        if not requirements:
            return []

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _generate_single(
            requirement: ImageRequirement,
        ) -> Tuple[ImageRequirement, ImageData, str]:
            async with semaphore:
                try:
                    method_enum = ImageMethodEnum(requirement.image_method)
                except ValueError:
                    method_enum = ImageMethodEnum.PEXELS

                image_request = ImageRequest(
                    keywords=requirement.keywords,
                    position=requirement.position,
                    image_method=method_enum,
                    section_title=requirement.section_title,
                    description=f"{requirement.type} image for {requirement.section_title or 'cover'}",
                )
                image_data = await self.image_strategy.get_image(image_request)
                cos_url = await self.cos_service.upload_async(image_data.url)
                logger.info(
                    "ParallelImageGenerator: 配图生成成功, position=%s, method=%s",
                    requirement.position,
                    image_data.method.value,
                )
                return requirement, image_data, cos_url

        raw_results = await asyncio.gather(
            *[_generate_single(req) for req in requirements],
            return_exceptions=True,
        )

        generated: List[Tuple[ImageRequirement, ImageData, str]] = []
        first_error: Exception | None = None
        for item in raw_results:
            if isinstance(item, Exception):
                logger.error("ParallelImageGenerator: 单张配图生成失败, error=%s", item)
                if first_error is None:
                    first_error = item
                continue
            generated.append(item)

        if first_error and (self.fail_fast or not generated):
            raise first_error

        return generated
