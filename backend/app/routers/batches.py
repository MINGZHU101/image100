"""批量处理：对本仓已注册工具子集串行入队（简化版）。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.compat.session_detail import to_frontend_asset
from app.deps import CurrentUser, DbDep
from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.services import tools as tools_service
from app.services.assets import to_asset_out
from app.tools.registry import get_tool

router = APIRouter(prefix="/batches", tags=["batches"])

# 第一版仅允许本仓已稳定工具
_ALLOWED = {
    "adjust_image",
    "remove_background",
    "flip_layer",
    "split_layers",
    "adjust_region",
    "upscale_image",
    "crop_canvas",
}


class BatchOp(BaseModel):
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)


class BatchCreateIn(BaseModel):
    asset_ids: list[UUID] = Field(min_length=1)
    operations: list[BatchOp] = Field(min_length=1)
    formats: list[str] = Field(default_factory=lambda: ["png"])


@router.post("")
async def create_batch(
    body: BatchCreateIn, db: DbDep, user: CurrentUser
) -> dict[str, Any]:
    """
    简化批量：对每个资产建临时会话并按 operations 顺序入队第一个工具，
    返回首个 run 作为批量进度入口（演示级，非原仓完整编排）。
    """
    del body.formats
    for op in body.operations:
        if op.tool not in _ALLOWED or get_tool(op.tool) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"批量暂不支持工具：{op.tool}",
            )

    from app.services import sessions as sessions_service

    first_run_id: UUID | None = None
    items: list[dict[str, Any]] = []
    for asset_id in body.asset_ids:
        asset = await db.get(Asset, asset_id)
        if asset is None or asset.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资产不存在")
        session_out = await sessions_service.create_session(db, user, asset_id)
        # 只跑流水线第一个操作，后续版本再串完整链
        op = body.operations[0]
        invoked = await tools_service.invoke_tool(
            db, session_out.id, op.tool, op.params
        )
        if first_run_id is None:
            first_run_id = invoked.run_id
        items.append(
            {
                "source": to_frontend_asset(to_asset_out(asset)),
                "status": "queued",
                "error": None,
                "outputs": [],
                "session_id": str(session_out.id),
                "run_id": str(invoked.run_id),
            }
        )

    assert first_run_id is not None
    run = await tools_service.get_run_compat(db, first_run_id)
    return run


@router.get("")
async def list_batches(db: DbDep, user: CurrentUser) -> list[dict[str, Any]]:
    """近期工具运行列表，凑合给批量历史页。"""
    result = await db.execute(
        select(ToolRun)
        .join(EditSession, ToolRun.session_id == EditSession.id)
        .where(EditSession.owner_id == user.id)
        .order_by(ToolRun.created_at.desc())
        .limit(20)
    )
    items = []
    for run in result.scalars().all():
        items.append(
            {
                "run": await tools_service.get_run_compat(db, run.id),
                "items": [],
                "created_at": run.created_at.isoformat(),
            }
        )
    return items


@router.get("/{run_id}")
async def get_batch(run_id: UUID, db: DbDep) -> dict[str, Any]:
    run = await tools_service.get_run_compat(db, run_id)
    return {"run": run, "items": [], "created_at": ""}
