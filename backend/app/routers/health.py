"""健康检查路由：探测 PostgreSQL 与 Redis。"""

import asyncio

from fastapi import APIRouter

from app.db import check_postgres, check_redis
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """并行探测中间件；始终 HTTP 200，异常依赖标为 error，整体可为 degraded。"""
    postgres_status, redis_status = await asyncio.gather(
        check_postgres(),
        check_redis(),
    )
    overall = "ok" if postgres_status == "ok" and redis_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        postgres=postgres_status,
        redis=redis_status,
    )
