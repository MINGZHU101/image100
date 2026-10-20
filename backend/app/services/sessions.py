"""编辑会话用例：创建、查询与选区同步。"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models import User
from app.models.edit_session import EditSession
from app.schemas.session import SessionOut
from app.services.assets import get_asset_or_404


def build_document(asset_id: UUID, storage_key: str, width: int, height: int) -> dict:
    """初始化单主图层 document。"""
    return {
        "version": 1,
        "canvas": {"width": width, "height": height},
        "layers": [
            {
                "id": "layer_main",
                "name": "主图层",
                "asset_id": str(asset_id),
                "asset_key": storage_key,
                "visible": True,
            }
        ],
        "active_layer_id": "layer_main",
        "selection": None,
    }


def to_session_out(row: EditSession) -> SessionOut:
    return SessionOut(
        id=row.id,
        title=row.title,
        document=row.document,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def create_session(session: AsyncSession, user: User, asset_id: UUID) -> SessionOut:
    from app.services import history as history_service

    asset = await get_asset_or_404(session, asset_id, user)
    document = build_document(
        asset_id=asset.id,
        storage_key=asset.storage_key,
        width=asset.width,
        height=asset.height,
    )
    row = EditSession(
        owner_id=user.id,
        title="商品编辑",
        document=document,
        history_seq=1,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    await history_service.ensure_initial_history(session, row)
    return to_session_out(row)


async def get_session_row(
    session: AsyncSession, session_id: UUID, user: User | None = None
) -> EditSession:
    row = await session.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if user is not None and row.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return row


async def get_session(
    session: AsyncSession, session_id: UUID, user: User | None = None
) -> SessionOut:
    return to_session_out(await get_session_row(session, session_id, user))


async def update_selection(
    session: AsyncSession,
    session_id: UUID,
    selection: dict[str, Any] | None,
) -> SessionOut:
    """写入或清除 document.selection。"""
    row = await session.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    document = dict(row.document or {})
    document["selection"] = selection
    row.document = document
    flag_modified(row, "document")
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return to_session_out(row)


async def clear_selection(session: AsyncSession, session_id: UUID) -> None:
    """工具成功后清空选区（若会话已不存在则忽略）。"""
    row = await session.get(EditSession, session_id)
    if row is None:
        return
    document = dict(row.document or {})
    if document.get("selection") is None and not document.get("selection_mask_asset_id"):
        return
    document["selection"] = None
    document.pop("selection_mask_asset_id", None)
    document.pop("selection_markers", None)
    row.document = document
    flag_modified(row, "document")
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()


async def update_layers(
    session: AsyncSession,
    session_id: UUID,
    *,
    layer_patches: list[dict[str, Any]],
    active_layer_id: str | None,
) -> SessionOut:
    """更新图层可见性与当前选中层。"""
    row = await session.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    document = dict(row.document or {})
    layers = list(document.get("layers") or [])
    patch_map = {item["id"]: item for item in layer_patches}

    new_layers: list[dict[str, Any]] = []
    for layer in layers:
        item = dict(layer)
        patch = patch_map.get(str(item.get("id")))
        if patch is not None and "visible" in patch and patch["visible"] is not None:
            item["visible"] = bool(patch["visible"])
        new_layers.append(item)

    if active_layer_id is not None:
        ids = {str(layer.get("id")) for layer in new_layers}
        if active_layer_id not in ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图层不存在：{active_layer_id}",
            )
        document["active_layer_id"] = active_layer_id

    document["layers"] = new_layers
    row.document = document
    flag_modified(row, "document")
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return to_session_out(row)

