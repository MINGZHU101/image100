"""ARQ 任务入队。"""

from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from app.config import get_settings


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


async def enqueue_tool_run(run_id: UUID) -> str:
    """将工具运行任务入队，返回 job_id。"""
    redis = await create_pool(_redis_settings())
    try:
        # _job_id 与 run_id 对齐，避免同一 run 重复入队
        job = await redis.enqueue_job(
            "execute_tool_run",
            str(run_id),
            _job_id=str(run_id),
        )
        if job is None:
            raise RuntimeError("入队失败：返回空 job")
        return job.job_id

    finally:
        await redis.aclose()
