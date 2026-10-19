"""导出会话可见图层（扁平化）。"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.deps import DbDep
from app.models.edit_session import EditSession
from app.services import runs as runs_service

router = APIRouter(prefix="/sessions", tags=["export"])


@router.get("/{session_id}/export")
async def export_session(session_id: UUID, db: DbDep) -> Response:
    """同步导出当前可见层合成后的 PNG。"""
    edit_session = await db.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    data = await runs_service.flatten_visible_layers(db, session_id)
    filename = f"image100-{session_id}.png"
    return Response(
        content=data,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
