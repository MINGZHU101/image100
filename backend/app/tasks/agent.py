"""ARQ：串行执行 Agent 计划。"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.services import agent as agent_service

logger = logging.getLogger(__name__)


def _session_factory() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def execute_agent_plan(ctx: dict, agent_run_id: str) -> dict:
    """Worker：按计划顺序 invoke_tool，等每步成功后再下一步。"""
    del ctx
    factory = _session_factory()
    async with factory() as session:
        try:
            return await agent_service.execute_plan_serial(session, UUID(agent_run_id))
        except Exception:
            logger.exception("execute_agent_plan 失败 id=%s", agent_run_id)
            raise
