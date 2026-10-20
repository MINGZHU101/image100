"""API 路由汇总。"""

from fastapi import APIRouter

from app.routers import (
    account,
    agent,
    assets,
    auth,
    batches,
    events,
    export,
    generations,
    health,
    sessions,
    tools,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(assets.router)
api_router.include_router(sessions.router)
api_router.include_router(tools.router)
api_router.include_router(events.router)
api_router.include_router(export.router)
api_router.include_router(agent.router)
api_router.include_router(generations.router)
api_router.include_router(batches.router)
