"""Agent 规划 / 确认 / 取消。"""

from uuid import UUID

from fastapi import APIRouter

from app.deps import DbDep
from app.schemas.agent import (
    AgentConfirmOut,
    AgentCreateIn,
    AgentRunOut,
    PlannerOptionsOut,
)
from app.services import agent as agent_service

router = APIRouter(tags=["agent"])


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
