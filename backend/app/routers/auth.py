"""真注册 / 登录（JWT Cookie）；保留 demo 一键。"""

from fastapi import APIRouter, HTTPException, Response, status

from app.config import get_settings
from app.deps import CurrentUser, DbDep
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.security import SESSION_COOKIE, issue_token
from app.services import auth as auth_service
from app.services import invite as invite_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _start_session(response: Response, user) -> UserOut:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        issue_token(user.id),
        max_age=settings.jwt_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    return UserOut.from_user(user)


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
