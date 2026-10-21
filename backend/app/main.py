"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from app.config import get_settings
from app.observability import configure_langsmith
from app.routers import api_router


@asynccontextmanager
async def lifespan(_application: FastAPI):
    """启动时尽量准备 RAG 索引（失败不阻断服务）。"""
    try:
        from app.rag.index import ensure_index

        ensure_index()
    except Exception:
        pass
    yield


def create_app() -> FastAPI:
    """组装应用：CORS、OpenAPI、/api 路由。"""
    configure_langsmith()
    settings = get_settings()
    application = FastAPI(
        title="电商商品视觉 image100",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
