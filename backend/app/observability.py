"""LangSmith 可观测：把配置同步到进程环境，供 LangChain/LangGraph SDK 自动追踪。"""

from __future__ import annotations

import os

from app.config import get_settings


def configure_langsmith() -> None:
    """有 Key 且开启 tracing 时写入环境变量；否则关闭。"""
    settings = get_settings()
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project or "image100"
    else:
        # 避免本地误开
        os.environ.setdefault("LANGSMITH_TRACING", "false")
