"""管理端：转盘全站记录与下月奖池配置。"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.deps import CurrentAdmin, DbDep
from app.services import audit as audit_service
from app.services import lucky_wheel as wheel_service

router = APIRouter(prefix="/lucky-wheel")


class NextPoolIn(BaseModel):
    costs: list[int] = Field(default_factory=list)
    slots: list[dict[str, Any]] = Field(default_factory=list)
    jackpot_prob_each: float | None = None


@router.get("/spins")
async def list_spins(
    _admin: CurrentAdmin,
    db: DbDep,
    q: str | None = None,
    period_ym: str | None = None,
    jackpot_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    items, total = await wheel_service.admin_list_spins(
        db,
        q=q,
        period_ym=period_ym,
        jackpot_only=jackpot_only,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/config")
async def get_config(_admin: CurrentAdmin, db: DbDep) -> dict:
    return await wheel_service.admin_get_config(db)


@router.put("/config/next")
async def put_next_config(
    admin: CurrentAdmin, db: DbDep, body: NextPoolIn
) -> dict:
    payload = body.model_dump(exclude_none=True)
    result = await wheel_service.admin_save_next_config(db, payload)
    await audit_service.write(
        db,
        admin,
        action="lucky_wheel.config_next",
        target_type="lucky_wheel",
        target_id="",
        detail=f"slots={len(body.slots)} costs={body.costs}",
    )
    await db.commit()
    return result
