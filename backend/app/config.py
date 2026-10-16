"""应用配置：统一从环境变量 / 项目根 .env 读取，禁止业务代码散落 os.getenv。"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/app/config.py → 项目根目录（含 .env / data）
ROOT_DIR = Path(__file__).resolve().parents[2]

_DEFAULT_CORS = "http://localhost:7301,http://127.0.0.1:7301"

# v2 演示用户固定 UUID（与迁移种子一致）
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"


class Settings(BaseSettings):
    """应用配置；未声明字段忽略。"""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    api_port: int = 7302

    database_url: str = (
        "postgresql+asyncpg://retouch:retouch_dev@192.168.137.128:7311/retouch"
    )
    redis_url: str = "redis://192.168.137.128:7312/0"

    # NoDecode：避免 pydantic-settings 把逗号分隔串当 JSON 解析
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:7301",
        "http://127.0.0.1:7301",
    ]

    # v2：本地存储
    storage_backend: str = "local"
    local_storage_dir: str = "./data"
    upload_max_bytes: int = 10 * 1024 * 1024

    # v3：去背策略 mock | rembg（本期仅实现 mock）
    matting_provider: str = "mock"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """支持环境变量写成逗号分隔字符串。"""
        if value is None or value == "":
            value = _DEFAULT_CORS
        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",")]
            return [item for item in parts if item]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def storage_root(self) -> Path:
        """本地存储绝对路径（相对路径基于项目根）。"""
        path = Path(self.local_storage_dir)
        if path.is_absolute():
            return path
        return (ROOT_DIR / path).resolve()


@lru_cache
def get_settings() -> Settings:
    """进程内单例，避免重复解析 .env。"""
    return Settings()
