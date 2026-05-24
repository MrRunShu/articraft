import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    server_port: int = 8567
    server_host: str = "0.0.0.0"

    db_host: str
    db_port: int = 3306
    db_name: str
    db_user: str
    db_password: str

    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    session_secret_key: str
    session_max_age: int = 2592000

    password_salt: str

    # DeepSeek AI
    deepseek_api_key: str
    deepseek_model: str = "deepseek-chat"

    # Pexels 图片搜索
    pexels_api_key: str = ""

    # 腾讯云 COS
    tencent_cos_secret_id: str = ""
    tencent_cos_secret_key: str = ""
    tencent_cos_region: str = ""
    tencent_cos_bucket: str = ""
    tencent_cos_domain: str = ""

    # Nano Banana（Gemini AI 生图）
    nano_banana_api_key: str = ""
    nano_banana_model: str = "gemini-2.0-flash-preview-image-generation"
    nano_banana_aspect_ratio: str = "16:9"

    # Stripe 支付
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_success_url: str = "http://localhost:5173/vip?payment=success"
    stripe_cancel_url: str = "http://localhost:5173/vip?payment=cancel"

    # Day 8：多智能体并行编排配置
    agent_image_max_concurrency: int = 3
    agent_image_fail_fast: bool = True

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
