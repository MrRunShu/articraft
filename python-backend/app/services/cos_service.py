import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class CosService:
    """腾讯云 COS 服务：上传图片并返回 CDN 域名链接"""

    def __init__(self):
        self._enabled = False
        self._bucket: Optional[str] = None
        self._region: Optional[str] = None
        self._domain: Optional[str] = None
        try:
            from app.config import settings
            if (
                settings.tencent_cos_secret_id
                and settings.tencent_cos_secret_key
                and settings.tencent_cos_bucket
                and settings.tencent_cos_region
            ):
                from qcloud_cos import CosConfig, CosS3Client
                config = CosConfig(
                    Region=settings.tencent_cos_region,
                    SecretId=settings.tencent_cos_secret_id,
                    SecretKey=settings.tencent_cos_secret_key,
                )
                self._client = CosS3Client(config)
                self._bucket = settings.tencent_cos_bucket
                self._region = settings.tencent_cos_region
                self._domain = settings.tencent_cos_domain.rstrip("/") if settings.tencent_cos_domain else None
                self._enabled = True
        except Exception as e:
            logger.warning(f"COS 初始化失败，将使用原始 URL: {e}")

    def use_direct_url(self, image_url: str) -> str:
        """上传图片到 COS 并返回 CDN 链接；未配置或上传失败时返回原始 URL"""
        if not self._enabled:
            return image_url
        # data URL（base64）不上传，直接返回
        if image_url.startswith("data:"):
            return image_url
        try:
            import httpx, asyncio
            image_bytes = asyncio.get_event_loop().run_until_complete(self._download(image_url))
            if not image_bytes:
                return image_url
            ext = self._guess_ext(image_url)
            key = f"articles/{uuid.uuid4().hex}{ext}"
            self._client.put_object(
                Bucket=self._bucket,
                Body=image_bytes,
                Key=key,
                ContentType=self._guess_content_type(ext),
            )
            if self._domain:
                return f"{self._domain}/{key}"
            return f"https://{self._bucket}.cos.{self._region}.myqcloud.com/{key}"
        except Exception as e:
            logger.error(f"COS 上传失败，使用原始 URL: {e}")
            return image_url

    async def upload_async(self, image_url: str) -> str:
        """异步版上传（供 Agent5 直接 await）"""
        if not self._enabled or image_url.startswith("data:"):
            return image_url
        try:
            image_bytes = await self._download(image_url)
            if not image_bytes:
                return image_url
            ext = self._guess_ext(image_url)
            key = f"articles/{uuid.uuid4().hex}{ext}"
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.put_object(
                    Bucket=self._bucket,
                    Body=image_bytes,
                    Key=key,
                    ContentType=self._guess_content_type(ext),
                ),
            )
            if self._domain:
                return f"{self._domain}/{key}"
            return f"https://{self._bucket}.cos.{self._region}.myqcloud.com/{key}"
        except Exception as e:
            logger.error(f"COS 上传失败，使用原始 URL: {e}")
            return image_url

    @staticmethod
    async def _download(url: str) -> Optional[bytes]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.content
        except Exception as e:
            logger.error(f"图片下载失败: {e}")
        return None

    @staticmethod
    def _guess_ext(url: str) -> str:
        from urllib.parse import urlparse
        path = urlparse(url).path.lower()
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            if path.endswith(ext):
                return ext
        return ".jpg"

    @staticmethod
    def _guess_content_type(ext: str) -> str:
        mapping = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return mapping.get(ext, "image/jpeg")
