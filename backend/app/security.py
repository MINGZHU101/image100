"""密码哈希与 JWT 会话 Cookie。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings

SESSION_COOKIE = "image100_session"
ADMIN_SESSION_COOKIE = "image100_admin_session"
_ALGORITHM = "HS256"
ROLE_USER = "user"
ROLE_ADMIN = "admin"


@dataclass(frozen=True)
class TokenPayload:
    subject_id: uuid.UUID
    role: str
    token_version: int = 0


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def issue_token(user_id: uuid.UUID, *, token_version: int = 0) -> str:
    """用户会话令牌（含 token_version，便于强制下线）。"""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "role": ROLE_USER,
        "tv": int(token_version),
        "exp": datetime.now(UTC) + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def issue_admin_token(admin_id: uuid.UUID) -> str:
    settings = get_settings()
    payload = {
        "sub": str(admin_id),
        "role": ROLE_ADMIN,
        "exp": datetime.now(UTC) + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def read_token_payload(token: str) -> TokenPayload | None:
    """解析任意会话令牌；无效统一返回 None。"""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
        role = str(payload.get("role") or ROLE_USER)
        return TokenPayload(
            subject_id=uuid.UUID(payload["sub"]),
            role=role,
            token_version=int(payload.get("tv") or 0),
        )
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        return None


def read_token(token: str) -> uuid.UUID | None:
    """兼容旧调用：仅返回用户 id（role=user）。"""
    parsed = read_token_payload(token)
    if parsed is None or parsed.role != ROLE_USER:
        return None
    return parsed.subject_id
