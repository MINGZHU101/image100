"""v10: 用户积分会员字段 + 积分流水 + generation owner

Revision ID: 20261020_0006
Revises: 20261019_0005
Create Date: 2026-10-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0006"
down_revision: Union[str, Sequence[str], None] = "20261019_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
# bcrypt(demo123)
DEMO_PASSWORD_HASH = "$2b$12$y0dIPvS.j26/SlEsXF/hR.rlUKSB6qfXJA5./4R4MG43AadTa50Y6"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("display_name", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "users",
        sa.Column("member_tier", sa.String(length=16), nullable=False, server_default="青铜"),
    )
    op.add_column(
        "users",
        sa.Column("points_balance", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("points_spent_total", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("last_checkin_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("avatar_key", sa.String(length=512), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "invite_reward_claimed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "point_ledgers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("remark", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_point_ledgers_user_id", "point_ledgers", ["user_id"])
    op.create_index("ix_point_ledgers_kind", "point_ledgers", ["kind"])

    op.add_column(
        "generation_runs",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_generation_runs_owner_id", "generation_runs", ["owner_id"])
    op.create_foreign_key(
        "fk_generation_runs_owner_id_users",
        "generation_runs",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 回填 demo：展示名、密码哈希、高积分便于演示（运行时仍走无限逻辑）
    op.execute(
        sa.text(
            "UPDATE users SET "
            "display_name = COALESCE(NULLIF(display_name, ''), '演示账号'), "
            f"password_hash = '{DEMO_PASSWORD_HASH}', "
            "points_balance = 999999, "
            "member_tier = '钻石' "
            f"WHERE id = '{DEMO_USER_ID}'::uuid"
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET display_name = username "
            "WHERE display_name IS NULL OR display_name = ''"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE generation_runs SET owner_id = '{DEMO_USER_ID}'::uuid "
            "WHERE owner_id IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_generation_runs_owner_id_users", "generation_runs", type_="foreignkey")
    op.drop_index("ix_generation_runs_owner_id", table_name="generation_runs")
    op.drop_column("generation_runs", "owner_id")

    op.drop_index("ix_point_ledgers_kind", table_name="point_ledgers")
    op.drop_index("ix_point_ledgers_user_id", table_name="point_ledgers")
    op.drop_table("point_ledgers")

    op.drop_column("users", "invite_reward_claimed")
    op.drop_column("users", "avatar_key")
    op.drop_column("users", "last_checkin_date")
    op.drop_column("users", "points_spent_total")
    op.drop_column("users", "points_balance")
    op.drop_column("users", "member_tier")
    op.drop_column("users", "display_name")
