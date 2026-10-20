"""个人中心：资料、签到、充值、邀请、流水、头像。"""

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.deps import CurrentUser, DbDep
from app.schemas.auth import (
    ChangePasswordIn,
    DisplayNameIn,
    ExchangePointsIn,
    InviteRedeemIn,
    LedgerOut,
    MockRechargeIn,
    UsageOut,
    UserOut,
)
from app.services import account as account_service
from app.services import auth as auth_service
from app.services import invite as invite_service
from app.services import points as points_service
from app.services import quota as quota_service
from app.services import wallet as wallet_service
from app.storage import get_storage

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/me")
async def account_me(user: CurrentUser, db: DbDep) -> dict:
    usage = await quota_service.usage_summary(db, user)
    return {"user": UserOut.from_user(user).model_dump(), "usage": usage}


@router.patch("/display-name")
async def patch_display_name(
    body: DisplayNameIn, user: CurrentUser, db: DbDep
) -> UserOut:
    try:
        updated = await auth_service.update_display_name(db, user, body.display_name)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return UserOut.from_user(updated)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePasswordIn, user: CurrentUser, db: DbDep) -> None:
    try:
        await auth_service.change_password(
            db,
            user,
            old_password=body.old_password,
            new_password=body.new_password,
            new_password_confirm=body.new_password_confirm,
        )
    except auth_service.PasswordMismatch:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "两次输入的新密码不一致") from None
    except auth_service.InvalidCredentials:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "旧密码不正确") from None
    return None


@router.post("/checkin")
async def checkin(user: CurrentUser, db: DbDep) -> dict:
    return await account_service.checkin(db, user)


@router.post("/mock-recharge")
async def mock_recharge(body: MockRechargeIn, user: CurrentUser, db: DbDep) -> dict:
    return await account_service.mock_recharge(db, user, body.yuan)


@router.post("/exchange-points")
async def exchange_points(body: ExchangePointsIn, user: CurrentUser, db: DbDep) -> dict:
    return await account_service.exchange_points(db, user, body.yuan)


@router.get("/ledger")
async def ledger(user: CurrentUser, db: DbDep, limit: int = 50) -> list[LedgerOut]:
    rows = await points_service.list_ledger(db, user.id, limit=min(limit, 100))
    return [
        LedgerOut(
            id=str(row.id),
            delta=row.delta,
            balance_after=row.balance_after,
            kind=row.kind,
            remark=row.remark or "",
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.get("/wallet-ledger")
async def wallet_ledger(user: CurrentUser, db: DbDep, limit: int = 50) -> list[LedgerOut]:
    rows = await wallet_service.list_ledger(db, user.id, limit=min(limit, 100))
    return [
        LedgerOut(
            id=str(row.id),
            delta=row.delta,
            balance_after=row.balance_after,
            kind=row.kind,
            remark=row.remark or "",
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.get("/usage")
async def usage(user: CurrentUser, db: DbDep) -> UsageOut:
    data = await quota_service.usage_summary(db, user)
    return UsageOut(**data)


@router.post("/invite-codes")
async def create_invite_code(user: CurrentUser, db: DbDep) -> dict:
    return await invite_service.create_code(db, user)


@router.get("/invite-codes/active")
async def active_invite_code(user: CurrentUser) -> dict | None:
    return await invite_service.peek_active_code(user)


@router.post("/invite-codes/redeem")
async def redeem_invite(body: InviteRedeemIn, user: CurrentUser, db: DbDep) -> UserOut:
    await invite_service.redeem(db, user, body.invite_code)
    await db.refresh(user)
    return UserOut.from_user(user)


@router.post("/avatar")
async def upload_avatar(
    user: CurrentUser,
    db: DbDep,
    file: UploadFile = File(...),
) -> UserOut:
    updated = await account_service.upload_avatar(db, user, file)
    return UserOut.from_user(updated)


@router.get("/avatar/{user_id}")
async def get_avatar(user_id: UUID, db: DbDep) -> Response:
    """头像公开可读（仅二进制，不含敏感信息）。"""
    from app.services import auth as auth_svc

    target = await auth_svc.get_by_id(db, user_id)
    if target is None or not target.avatar_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "头像不存在")
    storage = get_storage()
    if not storage.exists(target.avatar_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "头像文件不存在")
    data = storage.get(target.avatar_key)
    mime = "image/jpeg"
    key = target.avatar_key.lower()
    if key.endswith(".png"):
        mime = "image/png"
    elif key.endswith(".webp"):
        mime = "image/webp"
    return Response(content=data, media_type=mime)
