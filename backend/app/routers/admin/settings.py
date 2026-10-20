"""运营参数。"""

from fastapi import APIRouter

from app.deps import CurrentAdmin, DbDep
from app.schemas.admin import SettingsUpdateIn
from app.services import admin_ops as admin_ops_service
from app.services import app_settings as settings_service

router = APIRouter(prefix="/settings")


@router.get("")
async def get_settings(_admin: CurrentAdmin, db: DbDep) -> dict[str, str]:
    return await settings_service.list_all(db)


@router.put("")
async def put_settings(
    admin: CurrentAdmin, db: DbDep, body: SettingsUpdateIn
) -> dict[str, str]:
    return await admin_ops_service.update_settings(db, admin, body.model_dump(exclude_none=True))
