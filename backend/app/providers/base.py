"""规划器抽象。"""

from typing import Protocol

from app.config import get_settings
from app.providers.dashscope import DashscopePlanner
from app.providers.mock import MockPlanner


class PlannerProvider(Protocol):
    name: str

    async def plan(self, goal: str, context: str) -> tuple[str, list[dict]]:
        """返回 (reply, raw_steps)。raw_steps 项含 tool_name/params。"""
        ...


def get_planner(provider_name: str | None = None) -> PlannerProvider:
    """按名称创建规划器；未指定则用配置默认。"""
    settings = get_settings()
    name = (provider_name or settings.planner_provider or "dashscope").strip().lower()
    if name == "mock":
        return MockPlanner()
    if name == "dashscope":
        return DashscopePlanner()
    raise ValueError(f"未知规划器：{name}，可选 mock / dashscope")
