"""API 路由汇总。"""

from fastapi import APIRouter

from app.routers import assets, health, sessions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(assets.router)
api_router.include_router(sessions.router)
