"""计划结构校验：工具存在性、agent_exposed、参数、线性依赖。"""

from typing import Any

from pydantic import BaseModel, Field

from app.tools.registry import get_tool, list_agent_tools

MAX_STEPS = 6


class PlanStep(BaseModel):
    id: str
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class PlanError(Exception):
    """计划非法，应对用户返回中文原因。"""


def validate_plan(raw_steps: list[dict]) -> list[dict]:
    """校验并规范化计划步骤，返回可落库的 dict 列表。"""
    if not raw_steps:
        raise PlanError("没有可执行的步骤，请换一种说法或使用工具栏")
    if len(raw_steps) > MAX_STEPS:
        raise PlanError(f"计划超过 {MAX_STEPS} 步，请拆成多次说明")

    allowed = {item.name for item in list_agent_tools()}
    normalized: list[PlanStep] = []

    for index, item in enumerate(raw_steps, start=1):
        tool_name = str(item.get("tool_name") or item.get("tool") or "").strip()
        if not tool_name:
            raise PlanError(f"第 {index} 步缺少工具名")
        if tool_name not in allowed:
            raise PlanError(f"未知或不允许的工具：{tool_name}")

        tool = get_tool(tool_name)
        assert tool is not None
        try:
            params = tool.params_model.model_validate(item.get("params") or {}).model_dump()
        except Exception as exc:  # noqa: BLE001
            raise PlanError(f"工具 {tool_name} 参数无效：{exc}") from exc

        step_id = str(item.get("id") or f"s{index}")
        depends = item.get("depends_on")
        if depends is None:
            # 默认线性依赖前一步
            depends = [normalized[-1].id] if normalized else []
        step = PlanStep(
            id=step_id,
            tool_name=tool.name,
            params=params,
            depends_on=list(depends),
        )
        normalized.append(step)

    known = {step.id for step in normalized}
    for step in normalized:
        missing = [dep for dep in step.depends_on if dep not in known]
        if missing:
            raise PlanError(f"步骤 {step.id} 依赖了不存在的步骤")
    if _has_cycle(normalized):
        raise PlanError("计划步骤存在循环依赖")

    return [step.model_dump() for step in normalized]


def _has_cycle(steps: list[PlanStep]) -> bool:
    ids = [step.id for step in steps]
    incoming = {step_id: 0 for step_id in ids}
    outgoing: dict[str, list[str]] = {step_id: [] for step_id in ids}
    for step in steps:
        for dep in step.depends_on:
            outgoing[dep].append(step.id)
            incoming[step.id] += 1

    queue = [step_id for step_id, count in incoming.items() if count == 0]
    seen = 0
    while queue:
        node = queue.pop()
        seen += 1
        for nxt in outgoing[node]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                queue.append(nxt)
    return seen != len(ids)
