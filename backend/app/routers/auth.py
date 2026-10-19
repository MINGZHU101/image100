"""演示鉴权：保留登录页；固定账号一点即过，不做真注册。"""

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

from app.config import DEMO_USER_ID

router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"
_SESSION_COOKIE = "image100_demo_session"


class Credentials(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=64)


class UserOut(BaseModel):
    id: str
    username: str


def _demo_user() -> UserOut:
    return UserOut(id=DEMO_USER_ID, username=DEMO_USERNAME)


def _set_cookie(response: Response) -> None:
    response.set_cookie(
        _SESSION_COOKIE,
        DEMO_USER_ID,
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: Credentials, response: Response) -> UserOut:
    """演示环境：注册亦落到 DEMO 用户。"""
    del body
    _set_cookie(response)
    return _demo_user()


@router.post("/login")
async def login(body: Credentials, response: Response) -> UserOut:
    """demo/demo123 或任意账号（开发期放行）均可进入。"""
    del body
    _set_cookie(response)
    return _demo_user()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(_SESSION_COOKIE, path="/")
    return None


@router.get("/me")
async def me(request: Request) -> UserOut:
    """无 Cookie 返回 401，前端 RequireAuth 跳转登录页。"""
    from fastapi import HTTPException

    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return _demo_user()
