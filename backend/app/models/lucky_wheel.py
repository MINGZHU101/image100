"""幸运大转盘：抽奖记录（按自然月周期）。"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDBase


class LuckyWheelSpin(UUIDBase):
    """单次抽奖结果；同一用户同一周期内 slot_index 唯一。"""

    __tablename__ = "lucky_wheel_spins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    # 周期：Asia/Shanghai 的 YYYY-MM
    period_ym: Mapped[str] = mapped_column(String(7), index=True)
    # 本月第几次（从 1 起）
    spin_index: Mapped[int] = mapped_column(Integer)
    cost_yuan: Mapped[int] = mapped_column(Integer)
    slot_index: Mapped[int] = mapped_column(Integer)
    prize_kind: Mapped[str] = mapped_column(String(32))
    prize_label: Mapped[str] = mapped_column(String(64))
    # 实际入账积分（升级档可能为 0；钻石升级则 15000）
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    is_jackpot: Mapped[bool] = mapped_column(Boolean, default=False)
    # 脱敏前展示名快照（弹幕用）
    display_name_snapshot: Mapped[str] = mapped_column(String(64), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
