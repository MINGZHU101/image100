"""编辑会话路由（含原仓前端兼容入口）。"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.compat.session_detail import build_session_detail
from app.deps import CurrentUser, DbDep, assert_owner
from app.models.edit_session import EditSession
from app.schemas.layers import LayersPatchIn
from app.schemas.selection import SelectionPatchIn
from app.schemas.session import SessionOut
from app.services import sessions as sessions_service
from app.services import tools as tools_service
from app.services.assets import asset_file_url
from app.services.selection_mask import apply_brush_selection, selection_payload_from_document
from app.models.asset import Asset

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreateCompatIn(BaseModel):
    """兼容原仓 current_asset_id 与本仓 asset_id。"""

    asset_id: UUID | None = None
    current_asset_id: UUID | None = None
    asset_ids: list[UUID] | None = None
    title: str | None = None


class SessionPatchCompatIn(BaseModel):
    title: str | None = None
    current_asset_id: UUID | None = None


class ToolInvokeCompatIn(BaseModel):
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)


class SelectCompatIn(BaseModel):
    revision: int = 0
    points: list[dict[str, float]] | None = None
    strokes: list[list[dict[str, float]]] | None = None
    radius: float | None = 0.03
    append: bool = False


class ExportCompatIn(BaseModel):
    asset_ids: list[UUID] = Field(default_factory=list)


async def _owned_session(db: DbDep, session_id: UUID, user: CurrentUser) -> EditSession:
    row = await db.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    assert_owner(row.owner_id, user, detail="会话不存在")
    return row


@router.post("")
async def create_session(
    body: SessionCreateCompatIn, db: DbDep, user: CurrentUser
) -> dict[str, Any]:
    asset_id = body.asset_id or body.current_asset_id
    if asset_id is None and body.asset_ids:
        asset_id = body.asset_ids[0]
    if asset_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 asset_id")
    created = await sessions_service.create_session(db, user, asset_id)
    if body.title:
        row = await db.get(EditSession, created.id)
        if row is not None:
            row.title = body.title[:128]
            await db.commit()
            await db.refresh(row)
            return await build_session_detail(db, row)
    row = await db.get(EditSession, created.id)
    assert row is not None
    return await build_session_detail(db, row)


@router.get("")
async def list_sessions(db: DbDep, user: CurrentUser) -> list[dict[str, Any]]:
    result = await db.execute(
        select(EditSession)
        .where(EditSession.owner_id == user.id)
        .order_by(EditSession.updated_at.desc())
        .limit(50)
    )
    rows = list(result.scalars().all())
    items: list[dict[str, Any]] = []
    for row in rows:
        detail = await build_session_detail(db, row)
        items.append(
            {
                "id": detail["id"],
                "title": detail["title"],
                "revision": detail["revision"],
                "history_seq": detail["history_seq"],
                "original_asset_id": detail["original_asset_id"],
                "current_asset_id": detail["current_asset_id"],
                "created_at": detail["created_at"],
                "updated_at": detail["updated_at"],
            }
        )
    return items


@router.get("/{session_id}")
async def get_session(session_id: UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    row = await _owned_session(db, session_id, user)
    return await build_session_detail(db, row)


@router.patch("/{session_id}")
async def patch_session(
    session_id: UUID,
    body: SessionPatchCompatIn,
    db: DbDep,
    user: CurrentUser,
) -> dict[str, Any]:
    row = await _owned_session(db, session_id, user)
    if body.title is not None:
        row.title = body.title[:128]
        await db.commit()
        await db.refresh(row)
    # current_asset_id 本期仅作展示字段，不改 document
    return await build_session_detail(db, row)


@router.get("/{session_id}/history")
async def session_history(
    session_id: UUID, db: DbDep, user: CurrentUser
) -> list[dict[str, Any]]:
    from app.services import history as history_service

    await _owned_session(db, session_id, user)
    return await history_service.list_history(db, session_id)


@router.post("/{session_id}/tools")
async def invoke_tool_compat(
    session_id: UUID,
    body: ToolInvokeCompatIn,
    db: DbDep,
    user: CurrentUser,
) -> dict[str, Any]:
    """原仓：POST body {tool, params} → {run, session}。"""
    await _owned_session(db, session_id, user)
    # 图层显隐：本仓无独立工具，直接 PATCH document
    if body.tool == "set_layer_visible":
        layer_id = str(body.params.get("layer_id") or "")
        visible = bool(body.params.get("visible", True))
        if not layer_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 layer_id")
        await sessions_service.update_layers(
            db,
            session_id,
            layer_patches=[{"id": layer_id, "visible": visible}],
            active_layer_id=None,
        )
        row = await db.get(EditSession, session_id)
        assert row is not None
        detail = await build_session_detail(db, row)
        return {
            "run": {
                "id": "00000000-0000-0000-0000-000000000000",
                "tool": "set_layer_visible",
                "status": "succeeded",
                "progress": 100,
                "stage": "完成",
                "error": None,
                "prompt": None,
                "candidates": [],
                "result": {},
            },
            "session": detail,
        }

    invoked = await tools_service.invoke_tool(db, session_id, body.tool, body.params)
    run = await tools_service.get_run(db, invoked.run_id)
    row = await db.get(EditSession, session_id)
    assert row is not None
    detail = await build_session_detail(db, row)
    return {
        "run": {
            "id": str(run.id),
            "tool": run.tool_name,
            "status": run.status,
            "progress": run.progress,
            "stage": "",
            "error": run.error,
            "prompt": None,
            "candidates": [],
            "result": {},
        },
        "session": detail,
    }


@router.post("/{session_id}/undo")
async def undo_session(session_id: UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    from app.services import history as history_service

    await _owned_session(db, session_id, user)
    row = await history_service.undo(db, session_id)
    return await build_session_detail(db, row)


@router.post("/{session_id}/redo")
async def redo_session(session_id: UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    from app.services import history as history_service

    await _owned_session(db, session_id, user)
    row = await history_service.redo(db, session_id)
    return await build_session_detail(db, row)


@router.post("/{session_id}/selection/prepare", status_code=status.HTTP_204_NO_CONTENT)
async def prepare_selection(session_id: UUID, db: DbDep, user: CurrentUser) -> Response:
    """点选/SAM 预热：本期空操作。"""
    await _owned_session(db, session_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{session_id}/selection")
async def select_compat(
    session_id: UUID, body: SelectCompatIn, db: DbDep, user: CurrentUser
) -> dict[str, Any]:
    row = await _owned_session(db, session_id, user)
    from app.services.selection_mask import apply_point_selection

    try:
        if body.points:
            return await apply_point_selection(
                db, row, points=body.points, append=body.append
            )
        if not body.strokes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 strokes 或 points")
        return await apply_brush_selection(
            db,
            row,
            strokes=body.strokes,
            radius=body.radius or 0.03,
            append=body.append,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{session_id}/selection")
async def get_selection(
    session_id: UUID, db: DbDep, user: CurrentUser
) -> dict[str, Any] | None:
    row = await _owned_session(db, session_id, user)
    meta = selection_payload_from_document(row.document)
    if meta is None:
        return None
    asset = await db.get(Asset, UUID(meta["mask_asset_id"]))
    if asset is None:
        return None
    return {
        "revision": meta["revision"],
        "mask": {
            "id": str(asset.id),
            "kind": "mask",
            "source": "tool",
            "image_format": "png",
            "width": asset.width,
            "height": asset.height,
            "size_bytes": 0,
            "has_alpha": True,
            "created_at": asset.created_at.isoformat(),
            "url": asset_file_url(asset.id),
        },
        "markers": [],
    }


@router.delete("/{session_id}/selection", status_code=status.HTTP_204_NO_CONTENT)
async def clear_selection_compat(
    session_id: UUID, db: DbDep, user: CurrentUser
) -> Response:
    await _owned_session(db, session_id, user)
    await sessions_service.update_selection(db, session_id, None)
    row = await db.get(EditSession, session_id)
    if row is not None:
        document = dict(row.document or {})
        document.pop("selection_mask_asset_id", None)
        document["selection_revision"] = int(document.get("selection_revision") or 0) + 1
        row.document = document
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(row, "document")
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{session_id}/exports")
async def export_compat(
    session_id: UUID, body: ExportCompatIn, db: DbDep, user: CurrentUser
) -> Response:
    """原仓 zip 导出 → 本期返回扁平 PNG。"""
    del body
    from app.services import runs as runs_service

    await _owned_session(db, session_id, user)
    data = await runs_service.flatten_visible_layers(db, session_id)
    filename = f"export-{session_id}.png"
    return Response(
        content=data,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# —— 本仓原有 PATCH（精简前端 / 内部仍可用）——


@router.patch("/{session_id}/selection", response_model=SessionOut)
async def patch_selection(
    session_id: UUID,
    body: SelectionPatchIn,
    db: DbDep,
    user: CurrentUser,
) -> SessionOut:
    """同步选区到 document.selection；传 null 表示清除。"""
    await _owned_session(db, session_id, user)
    payload = None
    if body.selection is not None:
        payload = body.selection.model_dump()
    return await sessions_service.update_selection(db, session_id, payload)


@router.patch("/{session_id}/layers", response_model=SessionOut)
async def patch_layers(
    session_id: UUID,
    body: LayersPatchIn,
    db: DbDep,
    user: CurrentUser,
) -> SessionOut:
    """更新图层可见性与 active_layer_id。"""
    await _owned_session(db, session_id, user)
    patches = [item.model_dump(exclude_none=True) for item in body.layers]
    return await sessions_service.update_layers(
        db,
        session_id,
        layer_patches=patches,
        active_layer_id=body.active_layer_id,
    )
