"""工具规格：UI 与未来 Agent 共用的元数据。"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_run import ToolRun

# handler(session, run) -> {"asset_id": "..."} 等结果摘要
ToolHandler = Callable[[AsyncSession, ToolRun], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolSpec:
    """单个工具的完整定义。"""

    name: str
    label: str
    description: str
    params_model: type[BaseModel]
    handler: ToolHandler
    # 是否在工具栏展示
    ui_exposed: bool = True
    # 是否走 ARQ 队列（导出等可同步）
    queued: bool = True
