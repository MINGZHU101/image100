"""公告 CRUD。"""

from uuid import UUID

from fastapi import APIRouter

from app.deps import CurrentAdmin, DbDep
from app.schemas.admin import AnnouncementIn, AnnouncementOut
from app.services import admin_ops as admin_ops_service

router = APIRouter(prefix="/announcements")


def _out(row) -> AnnouncementOut:
    return AnnouncementOut(
        id=str(row.id),
        title=row.title,
        body=row.body or "",
        is_published=bool(row.is_published),
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.get("")
async def list_announcements(_admin: CurrentAdmin, db: DbDep) -> list[AnnouncementOut]:
    rows = await admin_ops_service.list_announcements(db)
    return [_out(r) for r in rows]


@router.post("")
async def create_announcement(
    admin: CurrentAdmin, db: DbDep, body: AnnouncementIn
) -> AnnouncementOut:
    row = await admin_ops_service.create_announcement(
        db,
        admin,
        title=body.title,
        body=body.body,
        is_published=body.is_published,
    )
    return _out(row)


@router.patch("/{announcement_id}")
async def update_announcement(
    admin: CurrentAdmin,
    db: DbDep,
    announcement_id: UUID,
    body: AnnouncementIn,
) -> AnnouncementOut:
    row = await admin_ops_service.update_announcement(
        db,
        admin,
        announcement_id,
        title=body.title,
        body=body.body,
        is_published=body.is_published,
    )
    return _out(row)
