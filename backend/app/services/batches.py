"""批量任务：用 ToolRun.params['_batch'] 关联同一批多图运行。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compat.session_detail import to_frontend_asset
from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.services.assets import to_asset_out
from app.services import tools as tools_service

BATCH_META_KEY = "_batch"


def batch_meta_of(run: ToolRun) -> dict[str, Any] | None:
    raw = (run.params or {}).get(BATCH_META_KEY)
    return raw if isinstance(raw, dict) else None


def attach_batch_meta(run: ToolRun, meta: dict[str, Any]) -> None:
    """写入批量元数据；工具 handler 用 pydantic 校验时会忽略多余字段。"""
    params = dict(run.params or {})
    params[BATCH_META_KEY] = meta
    run.params = params


def _map_item_status(status_value: str) -> str:
    if status_value == "queued":
        return "pending"
    return status_value


def _aggregate(statuses: list[str], progresses: list[int]) -> tuple[str, int, str]:
    """汇总一批运行的状态 / 进度 / 文案。"""
    if not statuses:
        return "failed", 0, "无任务"
    if any(s == "failed" for s in statuses) and all(
        s in ("succeeded", "failed", "canceled") for s in statuses
    ):
        # 全部结束且有失败
        if all(s == "failed" for s in statuses):
            return "failed", 100, "失败"
        return "succeeded", 100, "完成"
    if all(s in ("succeeded", "canceled") for s in statuses):
        return "succeeded", 100, "完成"
    if any(s in ("running", "queued") for s in statuses):
        avg = int(sum(progresses) / max(len(progresses), 1))
        return "running", avg, "处理中"
    return statuses[0], progresses[0] if progresses else 0, "处理中"


async def _source_asset_for_run(session: AsyncSession, run: ToolRun) -> Asset | None:
    """从会话文档第一图层取源图；回退到批量元数据中的 source_asset_ids。"""
    edit = await session.get(EditSession, run.session_id)
    if edit is not None:
        layers = (edit.document or {}).get("layers") or []
        if layers:
            raw = layers[0].get("asset_id")
            if raw:
                try:
                    asset = await session.get(Asset, UUID(str(raw)))
                    if asset is not None:
                        return asset
                except ValueError:
                    pass

    meta = batch_meta_of(run)
    if not meta:
        return None
    # 按 run 在 run_ids 中的下标对齐 source_asset_ids
    run_ids = [str(x) for x in (meta.get("run_ids") or [])]
    asset_ids = [str(x) for x in (meta.get("source_asset_ids") or [])]
    try:
        index = run_ids.index(str(run.id))
    except ValueError:
        return None
    if index < 0 or index >= len(asset_ids):
        return None
    try:
        return await session.get(Asset, UUID(asset_ids[index]))
    except ValueError:
        return None


async def _build_item(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    source = await _source_asset_for_run(session, run)
    outputs: list[dict[str, Any]] = []
    if run.result_asset_id is not None:
        result_asset = await session.get(Asset, run.result_asset_id)
        if result_asset is not None:
            outputs.append(to_frontend_asset(to_asset_out(result_asset)))

    source_payload = (
        to_frontend_asset(to_asset_out(source))
        if source is not None
        else {
            "id": "",
            "kind": "original",
            "source": "upload",
            "image_format": "png",
            "width": 0,
            "height": 0,
            "size_bytes": 0,
            "has_alpha": False,
            "created_at": "",
            "url": "",
        }
    )
    return {
        "source": source_payload,
        "status": _map_item_status(run.status),
        "error": run.error,
        "outputs": outputs,
        "session_id": str(run.session_id),
        "run_id": str(run.id),
    }


async def resolve_sibling_runs(session: AsyncSession, run: ToolRun) -> list[ToolRun]:
    """解析同一批的全部 ToolRun；无元数据时仅返回自身。"""
    meta = batch_meta_of(run)
    if not meta:
        return [run]
    raw_ids = meta.get("run_ids") or []
    runs: list[ToolRun] = []
    for raw in raw_ids:
        try:
            sibling = await session.get(ToolRun, UUID(str(raw)))
        except ValueError:
            continue
        if sibling is not None:
            runs.append(sibling)
    return runs or [run]


async def build_batch_payload(session: AsyncSession, run_id: UUID) -> dict[str, Any]:
    """组装前端 Batch 结构（含 items）。"""
    run = await session.get(ToolRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    siblings = await resolve_sibling_runs(session, run)
    items = [await _build_item(session, sibling) for sibling in siblings]
    statuses = [sibling.status for sibling in siblings]
    progresses = [sibling.progress for sibling in siblings]
    agg_status, agg_progress, agg_stage = _aggregate(statuses, progresses)

    compat = await tools_service.get_run_compat(session, run_id)
    compat["status"] = agg_status
    compat["progress"] = agg_progress
    compat["stage"] = agg_stage
    if agg_status == "failed":
        errors = [s.error for s in siblings if s.error]
        compat["error"] = errors[0] if errors else compat.get("error")

    created = min((s.created_at for s in siblings), default=run.created_at)
    return {
        "run": compat,
        "items": items,
        "created_at": created.isoformat() if created else "",
    }


async def list_batch_payloads(
    session: AsyncSession, user_id: UUID, *, limit: int = 20
) -> list[dict[str, Any]]:
    """只列出批量「队长」任务，避免把编辑器单次工具跑进历史。"""
    result = await session.execute(
        select(ToolRun)
        .join(EditSession, ToolRun.session_id == EditSession.id)
        .where(EditSession.owner_id == user_id)
        .order_by(ToolRun.created_at.desc())
        .limit(80)
    )
    leaders: list[ToolRun] = []
    seen: set[str] = set()
    for run in result.scalars().all():
        meta = batch_meta_of(run)
        if not meta:
            continue
        leader_id = str(meta.get("leader_id") or "")
        if not leader_id or leader_id in seen:
            continue
        if str(run.id) != leader_id:
            continue
        seen.add(leader_id)
        leaders.append(run)
        if len(leaders) >= limit:
            break

    payloads: list[dict[str, Any]] = []
    for leader in leaders:
        payloads.append(await build_batch_payload(session, leader.id))
    return payloads


async def collect_export_assets(
    session: AsyncSession, run_id: UUID
) -> list[tuple[str, bytes, str]]:
    """成功项的结果图：(文件名, 字节, mime)。"""
    from app.storage import get_storage

    run = await session.get(ToolRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    siblings = await resolve_sibling_runs(session, run)
    storage = get_storage()
    files: list[tuple[str, bytes, str]] = []
    index = 0
    for sibling in siblings:
        if sibling.status != "succeeded" or sibling.result_asset_id is None:
            continue
        asset = await session.get(Asset, sibling.result_asset_id)
        if asset is None:
            continue
        index += 1
        data = storage.get(asset.storage_key)
        ext = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }.get(asset.mime, "png")
        files.append((f"result_{index:02d}.{ext}", data, asset.mime))
    return files
