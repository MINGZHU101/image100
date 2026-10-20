"""操作日志。"""

from fastapi import APIRouter, Query

from app.deps import CurrentAdmin, DbDep
from app.services import admin_ops as admin_ops_service

router = APIRouter(prefix="/audit-logs")


@router.get("")
async def list_logs(
    _admin: CurrentAdmin,
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> dict:
    rows, total = await admin_ops_service.list_audit_logs(db, page=page, page_size=page_size)
    return {
        "items": [
            {
                "id": str(r.id),
                "admin_username": r.admin_username,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "detail": r.detail,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
