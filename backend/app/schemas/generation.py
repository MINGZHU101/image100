"""文生图请求/响应。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationCreateIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    count: int = Field(default=2, ge=1, le=4)
    image_provider: Literal["mock", "dashscope"] | None = None


class GenerationRunOut(BaseModel):
    id: UUID
    prompt: str
    params: dict
    image_provider: str
    status: str
    progress: int
    result_asset_ids: list[str]
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class GenerationCreateOut(BaseModel):
    generation_id: UUID
    status: str = "queued"


class ImageProviderOptionsOut(BaseModel):
    default_provider: Literal["mock", "dashscope"]
    dashscope_available: bool
    providers: list[Literal["mock", "dashscope"]]
    # 文生图模型白名单与默认值（前端备选）
    default_image_model: str
    image_models: list[str]
