"""管理员账号（与业务用户分表）。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDBase


class Admin(UUIDBase):
    __tablename__ = "admins"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(64), default="管理员")
