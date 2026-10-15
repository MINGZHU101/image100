"""健康检查路由：探测 PostgreSQL、Redis 与本地存储。"""

import asyncio

from fastapi import APIRouter

from app.db import check_postgres, check_redis, check_storage
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """并行探测依赖；始终 HTTP 200，异常标为 error，整体可为 degraded。"""
    postgres_status, redis_status = await asyncio.gather(
        check_postgres(),
        check_redis(),
    )
    # 本地磁盘探测为同步 IO，放到线程池避免阻塞事件循环
    storage_status = await asyncio.to_thread(check_storage)
    overall = (
        "ok"
        if postgres_status == "ok"
        and redis_status == "ok"
        and storage_status == "ok"
        else "degraded"
    )
    return HealthResponse(
        status=overall,
        postgres=postgres_status,
        redis=redis_status,
        storage=storage_status,
    )
