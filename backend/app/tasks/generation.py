"""ARQ：执行文生图。"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.services import generation as generation_service

logger = logging.getLogger(__name__)


def _session_factory() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def execute_generation(ctx: dict, generation_id: str) -> dict:
    del ctx
    factory = _session_factory()
    async with factory() as session:
        try:
            return await generation_service.execute_generation(session, UUID(generation_id))
        except Exception:
            logger.exception("execute_generation 失败 id=%s", generation_id)
            raise
