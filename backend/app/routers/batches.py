"""批量处理：多图同一工具子集串行入队，并用 params['_batch'] 关联。"""

from __future__ import annotations

import io
import zipfile
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.deps import CurrentUser, DbDep
from app.models.asset import Asset
from app.models.tool_run import ToolRun
from app.services import batches as batches_service
from app.services import tools as tools_service
from app.tools.registry import get_tool

router = APIRouter(prefix="/batches", tags=["batches"])

# 与前端批量页工具对齐
_ALLOWED = {
    "adjust_image",
    "remove_background",
    "replace_background",
    "upscale_image",
    "expand_canvas",
    "prepare_delivery_sizes",
    "flip_layer",
    "split_layers",
    "adjust_region",
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
    对每个资产建临时会话并入队流水线第一个工具；
    在各 ToolRun.params['_batch'] 写入关联，供进度页按批拉取 items。
    """
    del body.formats
    for op in body.operations:
        if op.tool not in _ALLOWED or get_tool(op.tool) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"批量暂不支持工具：{op.tool}",
            )

    from app.services import sessions as sessions_service

    op = body.operations[0]
    run_ids: list[UUID] = []
    asset_ids: list[UUID] = []

    for asset_id in body.asset_ids:
        asset = await db.get(Asset, asset_id)
        if asset is None or asset.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资产不存在")
        session_out = await sessions_service.create_session(db, user, asset_id)
        invoked = await tools_service.invoke_tool(
            db, session_out.id, op.tool, op.params
        )
        run_ids.append(invoked.run_id)
        asset_ids.append(asset_id)

    leader_id = run_ids[0]
    meta = {
        "leader_id": str(leader_id),
        "run_ids": [str(item) for item in run_ids],
        "source_asset_ids": [str(item) for item in asset_ids],
    }
    for run_id in run_ids:
        run = await db.get(ToolRun, run_id)
        if run is not None:
            batches_service.attach_batch_meta(run, meta)
    await db.commit()

    return await tools_service.get_run_compat(db, leader_id)


@router.get("")
async def list_batches(db: DbDep, user: CurrentUser) -> list[dict[str, Any]]:
    return await batches_service.list_batch_payloads(db, user.id)


@router.get("/{run_id}")
async def get_batch(run_id: UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    payload = await batches_service.build_batch_payload(db, run_id)
    # 校验归属：任一条目会话属于当前用户
    from app.models.edit_session import EditSession

    run = await db.get(ToolRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    edit = await db.get(EditSession, run.session_id)
    if edit is None or edit.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return payload


@router.get("/{run_id}/export")
async def export_batch(run_id: UUID, db: DbDep, user: CurrentUser) -> StreamingResponse:
    """打包成功结果为 zip。"""
    from app.models.edit_session import EditSession

    run = await db.get(ToolRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    edit = await db.get(EditSession, run.session_id)
    if edit is None or edit.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    files = await batches_service.collect_export_assets(db, run_id)
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可导出的成功结果",
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data, _mime in files:
            archive.writestr(name, data)
    buffer.seek(0)

    headers = {
        "Content-Disposition": "attachment; filename*=UTF-8''%E6%89%B9%E9%87%8F%E5%AF%BC%E5%87%BA.zip"
    }
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)
