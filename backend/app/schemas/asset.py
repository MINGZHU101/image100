"""资产相关请求/响应模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AssetOut(BaseModel):
    """资产对外信息。"""

    id: UUID
    storage_key: str
    width: int
    height: int
    mime: str
    created_at: datetime
    file_url: str = Field(description="前端加载图片的相对路径，如 /api/assets/{id}/file")

    model_config = {"from_attributes": True}


class AssetListOut(BaseModel):
    items: list[AssetOut]
