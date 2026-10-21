"""v12: 幸运大转盘抽奖记录表

Revision ID: 20261021_0009
Revises: 20261020_0008
Create Date: 2026-10-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261021_0009"
down_revision: Union[str, Sequence[str], None] = "20261020_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lucky_wheel_spins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_ym", sa.String(length=7), nullable=False),
        sa.Column("spin_index", sa.Integer(), nullable=False),
        sa.Column("cost_yuan", sa.Integer(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("prize_kind", sa.String(length=32), nullable=False),
        sa.Column("prize_label", sa.String(length=64), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_jackpot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "display_name_snapshot",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("remark", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_lucky_wheel_spins_user_id", "lucky_wheel_spins", ["user_id"]
    )
    op.create_index(
        "ix_lucky_wheel_spins_period_ym", "lucky_wheel_spins", ["period_ym"]
    )
    op.create_index(
        "ix_lucky_wheel_spins_user_period_slot",
        "lucky_wheel_spins",
        ["user_id", "period_ym", "slot_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lucky_wheel_spins_user_period_slot", table_name="lucky_wheel_spins"
    )
    op.drop_index("ix_lucky_wheel_spins_period_ym", table_name="lucky_wheel_spins")
    op.drop_index("ix_lucky_wheel_spins_user_id", table_name="lucky_wheel_spins")
    op.drop_table("lucky_wheel_spins")
