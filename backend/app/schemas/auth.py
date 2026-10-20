"""鉴权与用户对外模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.membership_rules import next_tier_progress
from app.models import User


class RegisterIn(BaseModel):
    account: str = Field(..., min_length=3, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=6, max_length=64)
    password_confirm: str = Field(..., min_length=6, max_length=64)
    invite_code: str | None = Field(default=None, max_length=16)

    @field_validator("account")
    @classmethod
    def account_charset(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.replace("_", "").isalnum():
            raise ValueError("账号仅支持字母、数字与下划线")
        return cleaned

    @model_validator(mode="after")
    def passwords_match(self) -> RegisterIn:
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        return self


class LoginIn(BaseModel):
    account: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=64)
    invite_code: str | None = Field(default=None, max_length=16)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)
    new_password_confirm: str = Field(..., min_length=6, max_length=64)

    @model_validator(mode="after")
    def passwords_match(self) -> ChangePasswordIn:
        if self.new_password != self.new_password_confirm:
            raise ValueError("两次输入的新密码不一致")
        return self


class DisplayNameIn(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=32)


class MockRechargeIn(BaseModel):
    yuan: int = Field(..., ge=1, le=1000)


class ExchangePointsIn(BaseModel):
    """用余额兑换积分：单位为元。"""

    yuan: int = Field(..., ge=1, le=1000)


class InviteRedeemIn(BaseModel):
    invite_code: str = Field(..., min_length=5, max_length=16)


class UserOut(BaseModel):
    id: str
    account: str
    display_name: str
    # 兼容旧前端字段：等同 display_name
    username: str
    member_tier: str
    wallet_balance: int
    points_balance: int
    points_spent_total: int
    invite_reward_claimed: bool
    newbie_gift_claimed: bool = False
    newbie_gift_eligible: bool = False
    is_frozen: bool = False
    last_checkin_date: str | None
    avatar_url: str | None
    next_tier: str | None
    points_to_next_tier: int
    created_at: str | None = None

    @classmethod
    def from_user(cls, user: User) -> UserOut:
        from app.membership_rules import DEMO_ACCOUNT

        next_tier, need = next_tier_progress(int(user.points_spent_total or 0))
        avatar_url = None
        if user.avatar_key:
            avatar_url = f"/api/account/avatar/{user.id}"
        claimed = bool(getattr(user, "newbie_gift_claimed", False))
        is_demo = user.username == DEMO_ACCOUNT
        return cls(
            id=str(user.id),
            account=user.username,
            display_name=user.display_name or user.username,
            username=user.display_name or user.username,
            member_tier=user.member_tier or "青铜",
            wallet_balance=int(getattr(user, "wallet_balance", 0) or 0),
            points_balance=int(user.points_balance or 0),
            points_spent_total=int(user.points_spent_total or 0),
            invite_reward_claimed=bool(user.invite_reward_claimed),
            newbie_gift_claimed=claimed,
            newbie_gift_eligible=(not claimed and not is_demo),
            is_frozen=bool(getattr(user, "is_frozen", False)),
            last_checkin_date=user.last_checkin_date.isoformat() if user.last_checkin_date else None,
            avatar_url=avatar_url,
            next_tier=next_tier,
            points_to_next_tier=need,
            created_at=user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        )


class LedgerOut(BaseModel):
    id: str
    delta: int
    balance_after: int
    kind: str
    remark: str
    created_at: str


class UsageOut(BaseModel):
    daily_used: int
    daily_limit: int | None
    concurrent_active: int
    concurrent_limit: int
    points_unlimited: bool
