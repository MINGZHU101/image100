"""FastAPI 依赖注入入口。"""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Admin, User
from app.security import (
    ADMIN_SESSION_COOKIE,
    ROLE_ADMIN,
    ROLE_USER,
    SESSION_COOKIE,
    read_token_payload,
)
from app.services import auth as auth_service
from app.services import admin_auth as admin_auth_service

_UNAUTHENTICATED = HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或会话已过期")
_FROZEN = HTTPException(status.HTTP_403_FORBIDDEN, "账号已冻结，请联系管理员")
_ADMIN_REQUIRED = HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")


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
    payload = read_token_payload(token)
    if payload is None or payload.role != ROLE_USER:
        raise _UNAUTHENTICATED
    user = await auth_service.get_by_id(session, payload.subject_id)
    if user is None:
        raise _UNAUTHENTICATED
    if bool(getattr(user, "is_frozen", False)):
        raise _FROZEN
    if int(getattr(user, "token_version", 0) or 0) != payload.token_version:
        raise _UNAUTHENTICATED
    return user


async def current_admin(
    session: DbDep,
    token: Annotated[str | None, Cookie(alias=ADMIN_SESSION_COOKIE)] = None,
) -> Admin:
    if token is None:
        raise _UNAUTHENTICATED
    payload = read_token_payload(token)
    if payload is None or payload.role != ROLE_ADMIN:
        raise _ADMIN_REQUIRED
    admin = await admin_auth_service.get_by_id(session, payload.subject_id)
    if admin is None:
        raise _UNAUTHENTICATED
    return admin


CurrentUser = Annotated[User, Depends(current_user)]
CurrentAdmin = Annotated[Admin, Depends(current_admin)]


def assert_owner(owner_id: UUID, user: User, *, detail: str = "资源不存在") -> None:
    """多租户隔离：非本人资源统一 404，避免泄露存在性。"""
    if owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
