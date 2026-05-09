class CosService:
    """腾讯云 COS 服务 — MVP 阶段直接返回原 URL，不做实际上传"""

    def use_direct_url(self, image_url: str) -> str:
        """MVP 阶段：直接使用图片原始 URL"""
        return image_url
