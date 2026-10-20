"""管理端 API 聚合。"""

from fastapi import APIRouter

from app.routers.admin import announcements, audit, dashboard, ledgers, ops, settings, users

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(dashboard.router)
router.include_router(users.router)
router.include_router(ledgers.router)
router.include_router(announcements.router)
router.include_router(settings.router)
router.include_router(audit.router)
router.include_router(ops.router)
