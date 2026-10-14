"""FastAPI 依赖注入入口。"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session


def get_app_settings() -> Settings:
    """配置单例，路由与服务统一从此获取。"""
    return get_settings()


async def get_db() -> AsyncIterator[AsyncSession]:
    """数据库 Session 依赖，为后续业务路由预留。"""
    async for session in get_session():
        yield session


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
