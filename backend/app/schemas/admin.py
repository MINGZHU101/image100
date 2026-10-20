"""管理端请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models import Admin


class AdminLoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=64)


class AdminOut(BaseModel):
    id: str
    username: str
    display_name: str
    created_at: str | None = None

    @classmethod
    def from_admin(cls, admin: Admin) -> AdminOut:
        return cls(
            id=str(admin.id),
            username=admin.username,
            display_name=admin.display_name or admin.username,
            created_at=admin.created_at.isoformat() if admin.created_at else None,
        )


class AdminCreateIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=64)
    display_name: str = Field(default="管理员", max_length=64)


class AdminChangePasswordIn(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)
    new_password_confirm: str = Field(..., min_length=6, max_length=64)

    @model_validator(mode="after")
    def passwords_match(self) -> AdminChangePasswordIn:
        if self.new_password != self.new_password_confirm:
            raise ValueError("两次输入的新密码不一致")
        return self


class AdjustPointsIn(BaseModel):
    delta: int = Field(..., ne=0)
    remark: str = Field(..., min_length=1, max_length=200)


class AdjustWalletIn(BaseModel):
    delta: int = Field(..., ne=0)
    remark: str = Field(..., min_length=1, max_length=200)


class FreezeIn(BaseModel):
    frozen: bool


class AnnouncementIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    body: str = Field(default="", max_length=4000)
    is_published: bool = True


class AnnouncementOut(BaseModel):
    id: str
    title: str
    body: str
    is_published: bool
    created_at: str
    updated_at: str | None = None


class SettingsUpdateIn(BaseModel):
    newbie_gift_points: int | None = None
    points_per_yuan: int | None = None
    mock_recharge_max_yuan: int | None = None
    checkin_points: dict[str, int] | None = None
    daily_ai_limit: dict[str, int] | None = None
    concurrent_run_limit: dict[str, int] | None = None


class BatchGrantIn(BaseModel):
    amount: int = Field(..., ge=1, le=100_000)
    remark: str = Field(..., min_length=1, max_length=200)
    # 为空表示全体未冻结用户；否则按账号列表
    accounts: list[str] | None = None
