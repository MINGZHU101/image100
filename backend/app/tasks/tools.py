"""执行工具运行的 ARQ 任务。"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.tool_run import ToolRun
from app.services import runs as runs_service
from app.tools.registry import get_tool

logger = logging.getLogger(__name__)


def _session_factory() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def execute_tool_run(ctx: dict, run_id: str) -> dict:
    """Worker 入口：加载 ToolRun → 调用 handler → 标记结果。"""
    factory = _session_factory()
    async with factory() as session:
        run = await session.get(ToolRun, UUID(run_id))
        if run is None:
            logger.error("ToolRun 不存在: %s", run_id)
            return {"ok": False, "error": "run_not_found"}

        tool = get_tool(run.tool_name)
        if tool is None:
            await runs_service.mark_failed(session, run, f"未知工具: {run.tool_name}")
            return {"ok": False, "error": "unknown_tool"}

        try:
            run.status = "running"
            await session.commit()
            result = await tool.handler(session, run)
            await runs_service.mark_succeeded(session, run)
            return {"ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001 — Worker 需捕获全部异常
            logger.exception("工具执行失败 run_id=%s", run_id)
            await session.rollback()
            # 重新加载 run，避免事务回滚后对象失效
            run = await session.get(ToolRun, UUID(run_id))
            if run is not None:
                await runs_service.mark_failed(session, run, str(exc))
            return {"ok": False, "error": str(exc)}
