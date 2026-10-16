"""v4: agent_runs 表

Revision ID: 20261016_0003
Revises: 20261016_0002
Create Date: 2026-10-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261016_0003"
down_revision: Union[str, Sequence[str], None] = "20261016_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("reply", sa.Text(), nullable=True),
        sa.Column(
            "plan",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("planner_provider", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "tool_run_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["edit_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_runs_session_id", table_name="agent_runs")
    op.drop_table("agent_runs")
