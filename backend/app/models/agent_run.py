"""Agent 规划运行：自然语言 goal → 计划 JSON → 确认执行。"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TIMESTAMPTZ, UUIDBase


class AgentRun(UUIDBase):
    __tablename__ = "agent_runs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("edit_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    # { "steps": [ {id, tool_name, params, depends_on}, ... ] }
    plan: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # planned | confirmed | running | done | cancelled | failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    # 实际使用的规划器：mock | dashscope
    planner_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 确认后产生的 tool_run id 列表
    tool_run_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now(), onupdate=func.now()
    )
