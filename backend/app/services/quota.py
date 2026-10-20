"""生产级配额：日 AI 次数与并发 run。"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.membership_rules import CONCURRENT_RUN_LIMIT, DAILY_AI_LIMIT
from app.models import User
from app.models.agent_run import AgentRun
from app.models.edit_session import EditSession
from app.models.generation_run import GenerationRun
from app.models.tool_run import ToolRun
from app.services import auth as auth_service

_SHANGHAI = ZoneInfo("Asia/Shanghai")


def shanghai_today() -> str:
    return datetime.now(_SHANGHAI).date().isoformat()


def shanghai_today_date():
    return datetime.now(_SHANGHAI).date()


def _daily_key(user_id) -> str:
    return f"quota:ai:{user_id}:{shanghai_today()}"


async def _redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


async def daily_used(user_id) -> int:
    client = await _redis()
    try:
        raw = await client.get(_daily_key(user_id))
        return int(raw or 0)
    finally:
        await client.aclose()


async def _active_run_count(session: AsyncSession, user: User) -> int:
    tool_q = await session.scalar(
        select(func.count())
        .select_from(ToolRun)
        .join(EditSession, ToolRun.session_id == EditSession.id)
        .where(
            EditSession.owner_id == user.id,
            ToolRun.status.in_(("queued", "running")),
        )
    )
    # planned 仅表示「等用户确认」，不占并发；只统计真正在执行的回合
    agent_q = await session.scalar(
        select(func.count())
        .select_from(AgentRun)
        .join(EditSession, AgentRun.session_id == EditSession.id)
        .where(
            EditSession.owner_id == user.id,
            AgentRun.status.in_(("confirmed", "running")),
        )
    )
    gen_q = await session.scalar(
        select(func.count())
        .select_from(GenerationRun)
        .where(
            GenerationRun.owner_id == user.id,
            GenerationRun.status.in_(("queued", "running")),
        )
    )
    return int(tool_q or 0) + int(agent_q or 0) + int(gen_q or 0)


async def ensure_can_start_ai(session: AsyncSession, user: User) -> None:
    """发起 AI 操作前：检查日额度与并发。"""
    if auth_service.is_demo_user(user):
        await _ensure_concurrent(session, user, limit=1)
        return

    daily_limit = DAILY_AI_LIMIT.get(user.member_tier, 20)
    used = await daily_used(user.id)
    if used >= daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "DAILY_QUOTA_EXCEEDED",
                "message": f"今日 AI 额度已用尽（{used}/{daily_limit}）",
                "used": used,
                "limit": daily_limit,
            },
        )

    concurrent_limit = CONCURRENT_RUN_LIMIT.get(user.member_tier, 1)
    await _ensure_concurrent(session, user, limit=concurrent_limit)


async def _ensure_concurrent(session: AsyncSession, user: User, *, limit: int) -> None:
    active = await _active_run_count(session, user)
    if active >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "CONCURRENT_LIMIT",
                "message": f"并发任务已满（{active}/{limit}），请稍后再试",
                "active": active,
                "limit": limit,
            },
        )


async def consume_daily_slot(user: User) -> None:
    """AI 操作成功入队后占用 1 次日额度；demo 跳过。"""
    if auth_service.is_demo_user(user):
        return
    client = await _redis()
    try:
        key = _daily_key(user.id)
        used = await client.incr(key)
        if used == 1:
            await client.expire(key, 60 * 60 * 48)
    finally:
        await client.aclose()


async def usage_summary(session: AsyncSession, user: User) -> dict:
    daily_limit = (
        None
        if auth_service.is_demo_user(user)
        else DAILY_AI_LIMIT.get(user.member_tier, 20)
    )
    concurrent_limit = (
        1
        if auth_service.is_demo_user(user)
        else CONCURRENT_RUN_LIMIT.get(user.member_tier, 1)
    )
    used = 0 if auth_service.is_demo_user(user) else await daily_used(user.id)
    active = await _active_run_count(session, user)
    return {
        "daily_used": used,
        "daily_limit": daily_limit,
        "concurrent_active": active,
        "concurrent_limit": concurrent_limit,
        "points_unlimited": auth_service.is_demo_user(user),
    }
