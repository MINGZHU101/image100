"""ToolRegistry：按名称查找工具。"""

from functools import lru_cache

from app.tools.base import ToolSpec
from app.tools.canvas_ops import FLIP_LAYER
from app.tools.extra import EXTRA_TOOLS
from app.tools.layers import SPLIT_LAYERS
from app.tools.marketing import GENERATE_MARKETING, PREPARE_DELIVERY
from app.tools.region import ADJUST_REGION
from app.tools.retouch import ADJUST_IMAGE, REMOVE_BACKGROUND


@lru_cache
def get_registry() -> dict[str, ToolSpec]:
    """返回 name → ToolSpec。"""
    tools = [
        ADJUST_IMAGE,
        ADJUST_REGION,
        REMOVE_BACKGROUND,
        FLIP_LAYER,
        SPLIT_LAYERS,
        *EXTRA_TOOLS,
        GENERATE_MARKETING,
        PREPARE_DELIVERY,
    ]
    return {item.name: item for item in tools}


def get_tool(name: str) -> ToolSpec | None:
    return get_registry().get(name)


def list_ui_tools() -> list[ToolSpec]:
    return [item for item in get_registry().values() if item.ui_exposed]


def list_agent_tools() -> list[ToolSpec]:
    """Agent 可绑定的工具（与 UI 共用 Registry）。"""
    return [item for item in get_registry().values() if item.agent_exposed]

