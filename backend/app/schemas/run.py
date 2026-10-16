"""工具运行相关请求/响应模型。"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ToolInvokeIn(BaseModel):
    """调用工具时的参数；允许空对象。"""

    params: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeOut(BaseModel):
    run_id: UUID
    status: str = "queued"


class ToolInfoOut(BaseModel):
    name: str
    label: str
    description: str


class RunOut(BaseModel):
    id: UUID
    session_id: UUID
    tool_name: str
    status: str
    progress: int
    params: dict[str, Any]
    result_asset_id: UUID | None = None
    error: str | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
