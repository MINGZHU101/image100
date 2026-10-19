"""编辑会话路由。"""

from uuid import UUID

from fastapi import APIRouter

from app.deps import DbDep
from app.schemas.layers import LayersPatchIn
from app.schemas.selection import SelectionPatchIn
from app.schemas.session import SessionCreateIn, SessionOut
from app.services import sessions as sessions_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
async def create_session(body: SessionCreateIn, db: DbDep) -> SessionOut:
    return await sessions_service.create_session(db, body.asset_id)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: UUID, db: DbDep) -> SessionOut:
    return await sessions_service.get_session(db, session_id)


@router.patch("/{session_id}/selection", response_model=SessionOut)
async def patch_selection(
    session_id: UUID,
    body: SelectionPatchIn,
    db: DbDep,
) -> SessionOut:
    """同步选区到 document.selection；传 null 表示清除。"""
    payload = None
    if body.selection is not None:
        payload = body.selection.model_dump()
    return await sessions_service.update_selection(db, session_id, payload)


@router.patch("/{session_id}/layers", response_model=SessionOut)
async def patch_layers(
    session_id: UUID,
    body: LayersPatchIn,
    db: DbDep,
) -> SessionOut:
    """更新图层可见性与 active_layer_id。"""
    patches = [
        item.model_dump(exclude_none=True)
        for item in body.layers
    ]
    return await sessions_service.update_layers(
        db,
        session_id,
        layer_patches=patches,
        active_layer_id=body.active_layer_id,
    )

