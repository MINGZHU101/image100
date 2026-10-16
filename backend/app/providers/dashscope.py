"""DashScope OpenAI 兼容规划器（langchain-openai）。"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_openai import ChatOpenAI

from app.agent.prompts import build_system_prompt
from app.config import get_settings
from app.tools.base import ToolSpec
from app.tools.registry import list_agent_tools


class PlannerUnavailable(Exception):
    """未配置 Key 或模型不可用。"""


class DashscopePlanner:
    name = "dashscope"

    async def plan(self, goal: str, context: str) -> tuple[str, list[dict]]:
        settings = get_settings()
        if not settings.dashscope_api_key:
            raise PlannerUnavailable(
                "未配置 DASHSCOPE_API_KEY，请切换到 Mock 或设置环境变量"
            )

        model = ChatOpenAI(
            model=settings.planner_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            temperature=0,
        )
        bound = model.bind_tools([_schema_of(spec) for spec in list_agent_tools()])
        message = await bound.ainvoke(
            [
                SystemMessage(build_system_prompt(context)),
                HumanMessage(goal),
            ]
        )

        steps: list[dict] = []
        for call in getattr(message, "tool_calls", None) or []:
            steps.append(
                {
                    "tool_name": call["name"],
                    "params": call.get("args") or {},
                }
            )
        reply = _text_of(message)
        return reply, steps


def _schema_of(spec: ToolSpec) -> dict:
    function = convert_to_openai_function(spec.params_model)
    function["name"] = spec.name
    function["description"] = spec.description
    return {"type": "function", "function": function}


def _text_of(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        ).strip()
    return ""
