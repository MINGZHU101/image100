"""Agent 规划相关请求/响应模型。"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCreateIn(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    # 前端 Mock / LLM 按钮覆盖；不传则用配置默认
    planner_provider: Literal["mock", "dashscope"] | None = None


class PlanStepOut(BaseModel):
    id: str
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class AgentRunOut(BaseModel):
    id: UUID
    session_id: UUID
    goal: str
    reply: str | None = None
    plan: dict[str, Any]
    status: str
    planner_provider: str
    error: str | None = None
    tool_run_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentConfirmOut(BaseModel):
    agent_run_id: UUID
    status: str
    tool_run_ids: list[str] = Field(default_factory=list)
    message: str = "已开始按序执行"


class PlannerOptionsOut(BaseModel):
    """前端切换按钮用：默认值与 dashscope 是否可用。"""

    default_provider: Literal["mock", "dashscope"]
    dashscope_available: bool
    providers: list[Literal["mock", "dashscope"]]
