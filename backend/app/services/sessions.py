"""编辑会话用例：创建、查询与选区同步。"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import DEMO_USER_ID
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


async def create_session(session: AsyncSession, asset_id: UUID) -> SessionOut:
    asset = await get_asset_or_404(session, asset_id)
    document = build_document(
        asset_id=asset.id,
        storage_key=asset.storage_key,
        width=asset.width,
        height=asset.height,
    )
    row = EditSession(
        owner_id=UUID(DEMO_USER_ID),
        title="商品编辑",
        document=document,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return to_session_out(row)


async def get_session(session: AsyncSession, session_id: UUID) -> SessionOut:
    row = await session.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return to_session_out(row)


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
    if document.get("selection") is None:
        return
    document["selection"] = None
    row.document = document
    flag_modified(row, "document")
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()

