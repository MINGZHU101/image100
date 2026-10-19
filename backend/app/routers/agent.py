"""Agent 规划 / 确认 / 取消（含原仓 messages 别名）。"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.deps import DbDep
from app.models.agent_run import AgentRun
from app.schemas.agent import (
    AgentConfirmOut,
    AgentCreateIn,
    AgentRunOut,
    PlannerOptionsOut,
)
from app.services import agent as agent_service

router = APIRouter(tags=["agent"])


class MessageCreateIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


def _map_turn_status(status_value: str) -> str:
    """本仓 Agent 状态 → 原仓 Turn.status（RunStatus）。"""
    mapping = {
        "planned": "queued",
        "confirmed": "queued",
        "running": "running",
        "done": "succeeded",
        "cancelled": "canceled",
        "failed": "failed",
    }
    return mapping.get(status_value, status_value)


def _map_step_status(agent_status: str, index: int, total: int) -> str:
    if agent_status == "planned":
        return "waiting"
    if agent_status in ("failed", "cancelled"):
        return "failed" if agent_status == "failed" else "canceled"
    if agent_status == "done":
        return "succeeded"
    if agent_status == "running":
        return "running" if index == 0 else "pending"
    return "pending"


def agent_run_to_turn(row: AgentRun) -> dict[str, Any]:
    steps_in = (row.plan or {}).get("steps") or []
    tool_run_ids = [str(item) for item in (row.tool_run_ids or [])]
    steps_out: list[dict[str, Any]] = []
    for index, step in enumerate(steps_in):
        tool = step.get("tool_name") or step.get("tool") or ""
        run_id = tool_run_ids[index] if index < len(tool_run_ids) else None
        steps_out.append(
            {
                "id": str(step.get("id") or f"step-{index}"),
                "tool": tool,
                "label": tool,
                "depends_on": list(step.get("depends_on") or []),
                "run_id": run_id,
                "status": _map_step_status(row.status, index, len(steps_in)),
            }
        )
    return {
        "id": str(row.id),
        "revision": 0,
        "goal": row.goal,
        "reply": row.reply or "",
        "status": _map_turn_status(row.status),
        "error": row.error,
        "created_at": row.created_at.isoformat(),
        "steps": steps_out,
    }


@router.get("/agent/planner-options", response_model=PlannerOptionsOut)
async def get_planner_options() -> PlannerOptionsOut:
    """前端 Mock / LLM 切换按钮用。"""
    return agent_service.planner_options()


@router.post(
    "/sessions/{session_id}/agent/runs",
    response_model=AgentRunOut,
)
async def create_agent_run(
    session_id: UUID,
    body: AgentCreateIn,
    db: DbDep,
) -> AgentRunOut:
    return await agent_service.create_agent_run(
        db,
        session_id,
        body.goal,
        body.planner_provider,
    )


@router.get(
    "/sessions/{session_id}/agent/runs/{agent_run_id}",
    response_model=AgentRunOut,
)
async def get_agent_run(
    session_id: UUID,
    agent_run_id: UUID,
    db: DbDep,
) -> AgentRunOut:
    del session_id
    return await agent_service.get_agent_run(db, agent_run_id)


@router.post(
    "/sessions/{session_id}/agent/runs/{agent_run_id}/confirm",
    response_model=AgentConfirmOut,
)
async def confirm_agent_run(
    session_id: UUID,
    agent_run_id: UUID,
    db: DbDep,
) -> AgentConfirmOut:
    return await agent_service.confirm_agent_run(db, session_id, agent_run_id)


@router.post(
    "/sessions/{session_id}/agent/runs/{agent_run_id}/cancel",
    response_model=AgentRunOut,
)
async def cancel_agent_run(
    session_id: UUID,
    agent_run_id: UUID,
    db: DbDep,
) -> AgentRunOut:
    return await agent_service.cancel_agent_run(db, session_id, agent_run_id)


# —— 原仓 messages 别名 ——


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: UUID, db: DbDep) -> list[dict[str, Any]]:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.session_id == session_id)
        .order_by(AgentRun.created_at.asc())
    )
    return [agent_run_to_turn(row) for row in result.scalars().all()]


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    body: MessageCreateIn,
    db: DbDep,
) -> dict[str, Any]:
    created = await agent_service.create_agent_run(db, session_id, body.text, None)
    row = await db.get(AgentRun, created.id)
    assert row is not None
    return agent_run_to_turn(row)


@router.post("/sessions/{session_id}/messages/{turn_id}/confirm")
async def confirm_message(
    session_id: UUID,
    turn_id: UUID,
    db: DbDep,
) -> dict[str, Any]:
    await agent_service.confirm_agent_run(db, session_id, turn_id)
    row = await db.get(AgentRun, turn_id)
    assert row is not None
    return agent_run_to_turn(row)


@router.post("/sessions/{session_id}/messages/{turn_id}/cancel")
async def cancel_message(
    session_id: UUID,
    turn_id: UUID,
    db: DbDep,
) -> dict[str, Any]:
    await agent_service.cancel_agent_run(db, session_id, turn_id)
    row = await db.get(AgentRun, turn_id)
    assert row is not None
    return agent_run_to_turn(row)


@router.post("/sessions/{session_id}/messages/{turn_id}/retry")
async def retry_message(
    session_id: UUID,
    turn_id: UUID,
    db: DbDep,
) -> dict[str, Any]:
    """重试：用原 goal 再规划一轮。"""
    old = await db.get(AgentRun, turn_id)
    if old is None or old.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    created = await agent_service.create_agent_run(
        db,
        session_id,
        old.goal,
        old.planner_provider,
    )
    row = await db.get(AgentRun, created.id)
    assert row is not None
    return agent_run_to_turn(row)
