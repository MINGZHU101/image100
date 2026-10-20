"""邀请概览、会话概览、批量发分、管理员账号。"""

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentAdmin, DbDep
from app.schemas.admin import (
    AdminChangePasswordIn,
    AdminCreateIn,
    AdminOut,
    BatchGrantIn,
)
from app.schemas.auth import UserOut
from app.services import admin_auth as admin_auth_service
from app.services import admin_ops as admin_ops_service

router = APIRouter()


@router.get("/invites")
async def invites(
    _admin: CurrentAdmin,
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    users, total = await admin_ops_service.list_invite_claimed(db, page=page, page_size=page_size)
    return {
        "items": [UserOut.from_user(u).model_dump() for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/sessions")
async def sessions_overview(
    _admin: CurrentAdmin,
    db: DbDep,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    items, total = await admin_ops_service.list_sessions_overview(
        db, q=q, page=page, page_size=page_size
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/batch-grant")
async def batch_grant(admin: CurrentAdmin, db: DbDep, body: BatchGrantIn) -> dict:
    return await admin_ops_service.batch_grant_points(
        db,
        admin,
        amount=body.amount,
        remark=body.remark,
        accounts=body.accounts,
    )


@router.get("/admins")
async def list_admins(_admin: CurrentAdmin, db: DbDep) -> list[AdminOut]:
    rows = await admin_auth_service.list_admins(db)
    return [AdminOut.from_admin(a) for a in rows]


@router.post("/admins", status_code=status.HTTP_201_CREATED)
async def create_admin(admin: CurrentAdmin, db: DbDep, body: AdminCreateIn) -> AdminOut:
    try:
        created = await admin_auth_service.create_admin(
            db,
            admin,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
        )
    except admin_auth_service.AdminTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "管理员账号已存在") from None
    return AdminOut.from_admin(created)


@router.post("/admins/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    admin: CurrentAdmin, db: DbDep, body: AdminChangePasswordIn
) -> None:
    try:
        await admin_auth_service.change_password(
            db,
            admin,
            old_password=body.old_password,
            new_password=body.new_password,
            new_password_confirm=body.new_password_confirm,
        )
    except admin_auth_service.PasswordMismatch:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "两次输入的新密码不一致") from None
    except admin_auth_service.InvalidAdminCredentials:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "旧密码不正确") from None
    return None
