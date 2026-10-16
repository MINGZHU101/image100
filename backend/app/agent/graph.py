"""
LangGraph 最小图：⑦ Graph 外壳 + ③ Plan&Execute 的 Planning/Verify。

架构说明（对齐课件）：
- ③ Plan & Execute：先产出结构化计划，执行在图外（确认后由 services 串行入队）
- ⑦ Graph/Workflow：StateGraph 编排 plan → verify
- HITL：产品层 PlanCard + REST confirm，不用图内 interrupt
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.plan import PlanError, validate_plan
from app.providers import get_planner
from app.tools.registry import get_tool


class AgentState(TypedDict):
    goal: str
    context: str
    planner_provider: str
    plan: list[dict]
    reply: str
    error: str


async def _plan_node(state: AgentState) -> dict:
    """调用规划器（mock / dashscope）产出原始步骤。"""
    planner = get_planner(state.get("planner_provider"))
    reply, raw_steps = await planner.plan(state["goal"], state["context"])
    return {"reply": reply or "", "plan": raw_steps, "error": ""}


def _verify_node(state: AgentState) -> dict:
    """服务端校验：未知工具 / 坏参数 / 环依赖一律拦截。"""
    try:
        steps = validate_plan(state.get("plan") or [])
        reply = state.get("reply") or ""
        if not reply:
            reply = _default_reply(steps)
        return {"plan": steps, "reply": reply, "error": ""}
    except PlanError as exc:
        return {"plan": [], "reply": str(exc), "error": str(exc)}


def _build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("plan", _plan_node)
    builder.add_node("verify", _verify_node)
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "verify")
    builder.add_edge("verify", END)
    return builder.compile()


_GRAPH = _build_graph()


async def run_planner(
    goal: str,
    context: str,
    *,
    planner_provider: str,
) -> tuple[str, list[dict], str | None]:
    """
    跑一轮 plan→verify。
    返回 (reply, validated_steps, error)。
    error 非空表示校验失败或无可执行步骤。
    """
    state = await _GRAPH.ainvoke(
        {
            "goal": goal,
            "context": context,
            "planner_provider": planner_provider,
            "plan": [],
            "reply": "",
            "error": "",
        }
    )
    error = state.get("error") or None
    plan = state.get("plan") or []
    reply = state.get("reply") or ""
    if not plan and not error:
        error = reply or "未能生成有效计划"
    return reply, plan, error


def _default_reply(steps: list[dict]) -> str:
    labels: list[str] = []
    for step in steps:
        tool = get_tool(step["tool_name"])
        labels.append(tool.label if tool else step["tool_name"])
    if len(labels) == 1:
        return f"好，将执行：{labels[0]}。确认后开始。"
    return f"将按以下步骤执行：{' → '.join(labels)}。确认后开始。"
