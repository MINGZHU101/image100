"""异步数据库引擎与连通性探测（PostgreSQL / Redis）。"""

from collections.abc import AsyncIterator

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 基类，业务模型从 v2 起继承。"""

    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    """请求级异步 Session，供依赖注入使用。"""
    async with SessionFactory() as session:
        yield session


async def check_postgres() -> str:
    """探测 PostgreSQL 是否可达；成功返回 ok，失败返回 error。"""
    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def check_redis() -> str:
    """探测 Redis 是否可达；成功返回 ok，失败返回 error。"""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
        return "ok"
    except Exception:
        return "error"
    finally:
        await client.aclose()


def check_storage() -> str:
    """探测本地存储目录是否可写。"""
    from app.storage import get_storage

    return get_storage().check_writable()
