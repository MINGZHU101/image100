"""v11: 新手礼包字段、冻结、管理员、公告、配置、审计

Revision ID: 20261020_0008
Revises: 20261020_0007
Create Date: 2026-10-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0008"
down_revision: Union[str, Sequence[str], None] = "20261020_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# bcrypt(admin123456)
ADMIN_PASSWORD_HASH = "$2b$12$UGV74eXWcFjW54X8od8EaeTTLyEwbA31HgQIeFq0PRH20eC3E.09y"
ADMIN_ID = "00000000-0000-0000-0000-0000000000aa"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "newbie_gift_claimed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_frozen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # 曾拿过注册赠送的用户视为已领礼包
    op.execute(
        sa.text(
            """
            UPDATE users SET newbie_gift_claimed = true
            WHERE id IN (
              SELECT DISTINCT user_id FROM point_ledgers WHERE kind = 'register_bonus'
            )
            """
        )
    )

    op.create_table(
        "admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False, server_default="管理员"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_admins_username", "admins", ["username"], unique=True)

    op.execute(
        sa.text(
            "INSERT INTO admins (id, username, password_hash, display_name) "
            f"VALUES ('{ADMIN_ID}'::uuid, 'admin', '{ADMIN_PASSWORD_HASH}', '超级管理员')"
        )
    )

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_username", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("target_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO app_settings (key, value) VALUES "
            "('newbie_gift_points', '2000'), "
            "('points_per_yuan', '10'), "
            "('mock_recharge_max_yuan', '1000')"
        )
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("announcements")
    op.drop_index("ix_admins_username", table_name="admins")
    op.drop_table("admins")
    op.drop_column("users", "token_version")
    op.drop_column("users", "is_frozen")
    op.drop_column("users", "newbie_gift_claimed")
