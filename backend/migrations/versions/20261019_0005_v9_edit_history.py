"""v9: edit_sessions.history_seq + edit_history 表

Revision ID: 20261019_0005
Revises: 20261016_0004
Create Date: 2026-10-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261019_0005"
down_revision: Union[str, Sequence[str], None] = "20261016_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "edit_sessions",
        sa.Column("history_seq", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("edit_sessions", "history_seq", server_default=None)

    op.create_table(
        "edit_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["edit_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "seq"),
    )
    op.create_index("ix_edit_history_session_id", "edit_history", ["session_id"])
    op.create_index("ix_edit_history_owner_id", "edit_history", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_edit_history_owner_id", table_name="edit_history")
    op.drop_index("ix_edit_history_session_id", table_name="edit_history")
    op.drop_table("edit_history")
    op.drop_column("edit_sessions", "history_seq")
