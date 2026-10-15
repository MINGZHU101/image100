"""编辑会话请求/响应模型。"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreateIn(BaseModel):
    asset_id: UUID


class SessionOut(BaseModel):
    id: UUID
    title: str | None
    document: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionCreateOut(BaseModel):
    """创建会话后返回，便于前端直接跳转。"""

    session: SessionOut
    message: str = Field(default="ok")
