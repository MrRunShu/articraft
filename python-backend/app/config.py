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

    # DeepSeek AI（当前默认启用）
    deepseek_api_key: str
    deepseek_model: str = "deepseek-chat"

    # DashScope AI（备用，配好后取消注释并在 .env 中填写）
    # dashscope_api_key: str = ""
    # dashscope_model: str = "qwen-plus"

    # Pexels 图片搜索（后续课程第4期启用）
    # pexels_api_key: str = ""

    # 腾讯云 COS（后续课程第4期启用）
    # tencent_cos_secret_id: str = ""
    # tencent_cos_secret_key: str = ""
    # tencent_cos_region: str = ""
    # tencent_cos_bucket: str = ""
    # tencent_cos_domain: str = ""

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
