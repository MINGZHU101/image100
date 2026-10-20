"""管理端仪表盘。"""

from fastapi import APIRouter

from app.deps import CurrentAdmin, DbDep
from app.services import admin_users as admin_users_service

router = APIRouter()


@router.get("/dashboard")
async def dashboard(_admin: CurrentAdmin, db: DbDep) -> dict:
    return await admin_users_service.dashboard_stats(db)
