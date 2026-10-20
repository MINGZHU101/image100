"""管理端用户管理。"""

from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.deps import CurrentAdmin, DbDep
from app.schemas.admin import AdjustPointsIn, AdjustWalletIn, FreezeIn
from app.schemas.auth import LedgerOut, UserOut
from app.services import admin_users as admin_users_service
from app.services import points as points_service
from app.services import wallet as wallet_service

router = APIRouter(prefix="/users")


def _user_row(user) -> dict:
    out = UserOut.from_user(user).model_dump()
    out["is_frozen"] = bool(user.is_frozen)
    out["newbie_gift_claimed"] = bool(user.newbie_gift_claimed)
    out["token_version"] = int(user.token_version or 0)
    return out


@router.get("")
async def list_users(
    _admin: CurrentAdmin,
    db: DbDep,
    q: str | None = None,
    member_tier: str | None = None,
    frozen: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    users, total = await admin_users_service.list_users(
        db, q=q, member_tier=member_tier, frozen=frozen, page=page, page_size=page_size
    )
    return {
        "items": [_user_row(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/export")
async def export_users(
    _admin: CurrentAdmin,
    db: DbDep,
    q: str | None = None,
    member_tier: str | None = None,
    frozen: bool | None = None,
) -> PlainTextResponse:
    csv_text = await admin_users_service.export_users_csv(
        db, q=q, member_tier=member_tier, frozen=frozen
    )
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )


@router.get("/{user_id}")
async def get_user(_admin: CurrentAdmin, db: DbDep, user_id: UUID) -> dict:
    user = await admin_users_service.get_user(db, user_id)
    point_rows = await points_service.list_ledger(db, user.id, limit=20)
    wallet_rows = await wallet_service.list_ledger(db, user.id, limit=20)
    return {
        "user": _user_row(user),
        "point_ledger": [
            LedgerOut(
                id=str(r.id),
                delta=r.delta,
                balance_after=r.balance_after,
                kind=r.kind,
                remark=r.remark or "",
                created_at=r.created_at.isoformat(),
            ).model_dump()
            for r in point_rows
        ],
        "wallet_ledger": [
            LedgerOut(
                id=str(r.id),
                delta=r.delta,
                balance_after=r.balance_after,
                kind=r.kind,
                remark=r.remark or "",
                created_at=r.created_at.isoformat(),
            ).model_dump()
            for r in wallet_rows
        ],
    }


@router.post("/{user_id}/adjust-points")
async def adjust_points(
    admin: CurrentAdmin, db: DbDep, user_id: UUID, body: AdjustPointsIn
) -> dict:
    user = await admin_users_service.get_user(db, user_id)
    updated = await admin_users_service.adjust_points(
        db, admin, user, delta=body.delta, remark=body.remark
    )
    return _user_row(updated)


@router.post("/{user_id}/adjust-wallet")
async def adjust_wallet(
    admin: CurrentAdmin, db: DbDep, user_id: UUID, body: AdjustWalletIn
) -> dict:
    user = await admin_users_service.get_user(db, user_id)
    updated = await admin_users_service.adjust_wallet(
        db, admin, user, delta=body.delta, remark=body.remark
    )
    return _user_row(updated)


@router.post("/{user_id}/freeze")
async def freeze_user(admin: CurrentAdmin, db: DbDep, user_id: UUID, body: FreezeIn) -> dict:
    user = await admin_users_service.get_user(db, user_id)
    updated = await admin_users_service.set_frozen(db, admin, user, frozen=body.frozen)
    return _user_row(updated)


@router.post("/{user_id}/force-logout")
async def force_logout(admin: CurrentAdmin, db: DbDep, user_id: UUID) -> dict:
    user = await admin_users_service.get_user(db, user_id)
    updated = await admin_users_service.force_logout(db, admin, user)
    return _user_row(updated)
