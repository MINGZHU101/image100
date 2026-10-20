"""运营参数读写（DB 优先，缺省回落 membership_rules）。"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.membership_rules import (
    CHECKIN_POINTS,
    CONCURRENT_RUN_LIMIT,
    DAILY_AI_LIMIT,
    MOCK_RECHARGE_MAX_YUAN,
    MOCK_RECHARGE_POINTS_PER_YUAN,
    REGISTER_BONUS,
)
from app.models import AppSetting

# 新手礼包默认积分（与历史 REGISTER_BONUS 同值）
DEFAULT_NEWBIE_GIFT_POINTS = REGISTER_BONUS

_DEFAULTS: dict[str, str] = {
    "newbie_gift_points": str(DEFAULT_NEWBIE_GIFT_POINTS),
    "points_per_yuan": str(MOCK_RECHARGE_POINTS_PER_YUAN),
    "mock_recharge_max_yuan": str(MOCK_RECHARGE_MAX_YUAN),
    "checkin_points": json.dumps(CHECKIN_POINTS, ensure_ascii=False),
    "daily_ai_limit": json.dumps(DAILY_AI_LIMIT, ensure_ascii=False),
    "concurrent_run_limit": json.dumps(CONCURRENT_RUN_LIMIT, ensure_ascii=False),
}


async def get_value(session: AsyncSession, key: str) -> str:
    row = await session.get(AppSetting, key)
    if row is not None and row.value != "":
        return row.value
    return _DEFAULTS.get(key, "")


async def get_int(session: AsyncSession, key: str, default: int) -> int:
    raw = await get_value(session, key)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


async def get_json_dict(session: AsyncSession, key: str, default: dict) -> dict:
    raw = await get_value(session, key)
    if not raw:
        return dict(default)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return dict(default)


async def newbie_gift_points(session: AsyncSession) -> int:
    return await get_int(session, "newbie_gift_points", DEFAULT_NEWBIE_GIFT_POINTS)


async def points_per_yuan(session: AsyncSession) -> int:
    return await get_int(session, "points_per_yuan", MOCK_RECHARGE_POINTS_PER_YUAN)


async def mock_recharge_max_yuan(session: AsyncSession) -> int:
    return await get_int(session, "mock_recharge_max_yuan", MOCK_RECHARGE_MAX_YUAN)


async def checkin_points_table(session: AsyncSession) -> dict[str, int]:
    raw = await get_json_dict(session, "checkin_points", CHECKIN_POINTS)
    return {str(k): int(v) for k, v in raw.items()}


async def list_all(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(AppSetting))
    stored = {row.key: row.value for row in result.scalars().all()}
    merged = dict(_DEFAULTS)
    merged.update(stored)
    return merged


async def upsert_many(session: AsyncSession, updates: dict[str, str]) -> dict[str, str]:
    """写入配置键值；不 commit，由调用方统一提交。"""
    for key, value in updates.items():
        if key not in _DEFAULTS:
            continue
        row = await session.get(AppSetting, key)
        if row is None:
            session.add(AppSetting(key=key, value=str(value)))
        else:
            row.value = str(value)
    await session.flush()
    return await list_all(session)
