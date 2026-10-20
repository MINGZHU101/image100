"""邀请码：Redis TTL + 双方积分奖励。"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.membership_rules import (
    INVITE_ALPHABET,
    INVITE_CODE_LENGTH,
    INVITE_REWARD,
    INVITE_TTL_SECONDS,
)
from app.models import User
from app.services import auth as auth_service
from app.services import points as points_service

_REDIS_PREFIX = "invite:code:"
_USER_ACTIVE_PREFIX = "invite:user:"


async def _redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


def _random_code() -> str:
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


async def create_code(session: AsyncSession, inviter: User) -> dict:
    """生成五位邀请码；同一用户新码会使旧码失效。"""
    del session
    client = await _redis()
    try:
        old = await client.get(f"{_USER_ACTIVE_PREFIX}{inviter.id}")
        if old:
            await client.delete(f"{_REDIS_PREFIX}{old}")

        code = _random_code()
        # 极低概率冲突时重试
        for _ in range(8):
            if not await client.exists(f"{_REDIS_PREFIX}{code}"):
                break
            code = _random_code()
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "邀请码生成失败，请重试")

        await client.setex(f"{_REDIS_PREFIX}{code}", INVITE_TTL_SECONDS, str(inviter.id))
        await client.setex(f"{_USER_ACTIVE_PREFIX}{inviter.id}", INVITE_TTL_SECONDS, code)
        expires_at = datetime.now(UTC) + timedelta(seconds=INVITE_TTL_SECONDS)
        return {"code": code, "expires_at": expires_at.isoformat(), "ttl_seconds": INVITE_TTL_SECONDS}
    finally:
        await client.aclose()


async def peek_active_code(inviter: User) -> dict | None:
    client = await _redis()
    try:
        code = await client.get(f"{_USER_ACTIVE_PREFIX}{inviter.id}")
        if not code:
            return None
        ttl = await client.ttl(f"{_REDIS_PREFIX}{code}")
        if ttl is None or ttl < 0:
            return None
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        return {"code": code, "expires_at": expires_at.isoformat(), "ttl_seconds": ttl}
    finally:
        await client.aclose()


async def redeem(
    session: AsyncSession,
    invitee: User,
    code: str | None,
) -> bool:
    """
    兑换邀请码。成功返回 True；未填码返回 False。
    已领过 / 无效 / 自邀抛 HTTPException。
    """
    if not code or not code.strip():
        return False
    cleaned = code.strip().upper()
    if invitee.invite_reward_claimed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "您已领取过邀请奖励")

    client = await _redis()
    try:
        inviter_id_raw = await client.get(f"{_REDIS_PREFIX}{cleaned}")
        if not inviter_id_raw:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "邀请码无效或已过期")
        inviter_id = uuid.UUID(inviter_id_raw)
    finally:
        await client.aclose()

    if inviter_id == invitee.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能使用自己的邀请码")

    inviter = await auth_service.get_by_id(session, inviter_id)
    if inviter is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "邀请码无效或已过期")

    await points_service.credit(
        session,
        invitee,
        amount=INVITE_REWARD,
        kind="invite_reward",
        remark=f"填写邀请码 {cleaned}",
    )
    await points_service.credit(
        session,
        inviter,
        amount=INVITE_REWARD,
        kind="invite_reward",
        remark=f"好友 {invitee.username} 使用邀请码",
    )
    invitee.invite_reward_claimed = True
    await session.commit()
    await session.refresh(invitee)
    return True
