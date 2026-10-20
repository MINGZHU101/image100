"""用户表：登录账号、展示名、会员积分与头像。"""

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDBase


class User(UUIDBase):
    __tablename__ = "users"

    # 登录账号（唯一）；历史字段名 username，语义为 account
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64), default="")
    password_hash: Mapped[str] = mapped_column(String(255))

    member_tier: Mapped[str] = mapped_column(String(16), default="青铜")
    # 账户余额（元，模拟充值优先入账，可再兑换积分）
    wallet_balance: Mapped[int] = mapped_column(Integer, default=0)
    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    points_spent_total: Mapped[int] = mapped_column(Integer, default=0)
    last_checkin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    avatar_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 是否已成功领取过邀请奖励（一生一次）
    invite_reward_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
