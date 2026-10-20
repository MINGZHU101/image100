"""v10: 账户余额 + 余额流水

Revision ID: 20261020_0007
Revises: 20261020_0006
Create Date: 2026-10-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0007"
down_revision: Union[str, Sequence[str], None] = "20261020_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("wallet_balance", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "wallet_ledgers",
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
    op.create_index("ix_wallet_ledgers_user_id", "wallet_ledgers", ["user_id"])
    op.create_index("ix_wallet_ledgers_kind", "wallet_ledgers", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_wallet_ledgers_kind", table_name="wallet_ledgers")
    op.drop_index("ix_wallet_ledgers_user_id", table_name="wallet_ledgers")
    op.drop_table("wallet_ledgers")
    op.drop_column("users", "wallet_balance")
