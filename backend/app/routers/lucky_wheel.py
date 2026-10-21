"""用户端：幸运大转盘。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.deps import CurrentUser, DbDep
from app.services import lucky_wheel as wheel_service

router = APIRouter(prefix="/lucky-wheel", tags=["lucky-wheel"])


class SpinIn(BaseModel):
    confirmed: bool = Field(description="二次确认后为 true")


@router.get("/state")
async def wheel_state(user: CurrentUser, db: DbDep) -> dict:
    return await wheel_service.get_state(db, user)


@router.get("/barrage")
async def wheel_barrage(_user: CurrentUser, db: DbDep) -> list[dict]:
    return await wheel_service.list_barrage(db, limit=10)


@router.post("/spin")
async def wheel_spin(body: SpinIn, user: CurrentUser, db: DbDep) -> dict:
    return await wheel_service.spin(db, user, confirmed=body.confirmed)
