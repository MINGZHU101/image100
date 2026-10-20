"""真注册 / 登录（JWT Cookie）；管理员登录；保留 demo 一键。"""

from fastapi import APIRouter, HTTPException, Response, status

from app.config import get_settings
from app.deps import CurrentAdmin, CurrentUser, DbDep
from app.schemas.admin import AdminLoginIn, AdminOut
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.security import (
    ADMIN_SESSION_COOKIE,
    SESSION_COOKIE,
    issue_admin_token,
    issue_token,
)
from app.services import admin_auth as admin_auth_service
from app.services import auth as auth_service
from app.services import invite as invite_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _start_session(response: Response, user) -> UserOut:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        issue_token(user.id, token_version=int(getattr(user, "token_version", 0) or 0)),
        max_age=settings.jwt_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    return UserOut.from_user(user)


def _start_admin_session(response: Response, admin) -> AdminOut:
    settings = get_settings()
    response.set_cookie(
        ADMIN_SESSION_COOKIE,
        issue_admin_token(admin.id),
        max_age=settings.jwt_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    return AdminOut.from_admin(admin)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, response: Response, db: DbDep) -> UserOut:
    try:
        user = await auth_service.register(
            db,
            account=body.account,
            display_name=body.display_name,
            password=body.password,
            password_confirm=body.password_confirm,
        )
    except auth_service.PasswordMismatch:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "两次输入的密码不一致") from None
    except auth_service.AccountTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "该账号已被占用") from None

    # 先发会话，再兑邀请：邀请码无效时仍完成注册登录
    out = _start_session(response, user)
    if body.invite_code:
        try:
            await invite_service.redeem(db, user, body.invite_code)
            await db.refresh(user)
            out = UserOut.from_user(user)
        except HTTPException:
            pass
    return out


@router.post("/login")
async def login(body: LoginIn, response: Response, db: DbDep) -> UserOut:
    try:
        user = await auth_service.authenticate(db, body.account, body.password)
    except auth_service.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误") from None
    except auth_service.AccountFrozen:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已冻结，请联系管理员") from None

    out = _start_session(response, user)
    if body.invite_code:
        try:
            await invite_service.redeem(db, user, body.invite_code)
            await db.refresh(user)
            out = UserOut.from_user(user)
        except HTTPException:
            # 登录成功；邀请失败可在个人中心补填
            pass
    return out


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return None


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.from_user(user)


@router.post("/admin/login")
async def admin_login(body: AdminLoginIn, response: Response, db: DbDep) -> AdminOut:
    try:
        admin = await admin_auth_service.authenticate(db, body.username, body.password)
    except admin_auth_service.InvalidAdminCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "管理员账号或密码错误") from None
    return _start_admin_session(response, admin)


@router.post("/admin/logout", status_code=status.HTTP_204_NO_CONTENT)
async def admin_logout(response: Response) -> None:
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
    return None


@router.get("/admin/me")
async def admin_me(admin: CurrentAdmin) -> AdminOut:
    return AdminOut.from_admin(admin)
