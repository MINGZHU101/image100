"""导出会话主图层。"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.deps import DbDep
from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.storage import get_storage

router = APIRouter(prefix="/sessions", tags=["export"])


@router.get("/{session_id}/export")
async def export_session(session_id: UUID, db: DbDep) -> Response:
    """同步导出当前主图层文件流。"""
    edit_session = await db.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    layers = (edit_session.document or {}).get("layers") or []
    if not layers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="会话无图层")

    asset_id = UUID(str(layers[0]["asset_id"]))
    asset = await db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资产不存在")

    storage = get_storage()
    if not storage.exists(asset.storage_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    data = storage.get(asset.storage_key)
    filename = f"image100-{session_id}.png"
    return Response(
        content=data,
        media_type=asset.mime or "image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
