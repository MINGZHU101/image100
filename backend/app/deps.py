"""FastAPI 依赖注入入口。"""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.models import User
from app.security import SESSION_COOKIE, read_token
from app.services import auth as auth_service

_UNAUTHENTICATED = HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或会话已过期")


def get_app_settings() -> Settings:
    """配置单例，路由与服务统一从此获取。"""
    return get_settings()


async def get_db() -> AsyncIterator[AsyncSession]:
    """数据库 Session 依赖。"""
    async for session in get_session():
        yield session


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def current_user(
    session: DbDep,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    if token is None:
        raise _UNAUTHENTICATED
    user_id = read_token(token)
    if user_id is None:
        raise _UNAUTHENTICATED
    user = await auth_service.get_by_id(session, user_id)
    if user is None:
        raise _UNAUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def assert_owner(owner_id: UUID, user: User, *, detail: str = "资源不存在") -> None:
    """多租户隔离：非本人资源统一 404，避免泄露存在性。"""
    if owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
