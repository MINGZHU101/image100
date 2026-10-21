"""幸运大转盘奖池默认配置与读写（当前月 / 下月）。"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting

# 费用：第 10、11 次均为 648
DEFAULT_COSTS: list[int] = [2, 4, 8, 16, 32, 64, 128, 256, 512, 648, 648]

# 积分格权重 9→1；两大奖各占初始概率 2%（不写 weight，由 jackpot_prob_each 处理）
DEFAULT_SLOTS: list[dict[str, Any]] = [
    {"index": 0, "kind": "points", "label": "4 积分", "points": 4, "weight": 9},
    {"index": 1, "kind": "points", "label": "8 积分", "points": 8, "weight": 8},
    {"index": 2, "kind": "points", "label": "16 积分", "points": 16, "weight": 7},
    {"index": 3, "kind": "points", "label": "32 积分", "points": 32, "weight": 6},
    {"index": 4, "kind": "points", "label": "64 积分", "points": 64, "weight": 5},
    {"index": 5, "kind": "points", "label": "128 积分", "points": 128, "weight": 4},
    {"index": 6, "kind": "points", "label": "256 积分", "points": 256, "weight": 3},
    {"index": 7, "kind": "points", "label": "512 积分", "points": 512, "weight": 2},
    {"index": 8, "kind": "points", "label": "1024 积分", "points": 1024, "weight": 1},
    {
        "index": 9,
        "kind": "tier_up",
        "label": "会员升一级",
        "points": 0,
        "weight": 0,
        "jackpot": True,
    },
    {
        "index": 10,
        "kind": "jackpot_points",
        "label": "12000 积分",
        "points": 12000,
        "weight": 0,
        "jackpot": True,
    },
]

JACKPOT_PROB_EACH = 0.02
DIAMOND_TIER_UP_POINTS = 15_000

KEY_CURRENT = "lucky_wheel_pool_current"
KEY_NEXT = "lucky_wheel_pool_next"
KEY_PERIOD = "lucky_wheel_active_period"


def default_pool() -> dict[str, Any]:
    """内置默认奖池（前端不展示概率）。"""
    return {
        "costs": list(DEFAULT_COSTS),
        "slots": deepcopy(DEFAULT_SLOTS),
        "jackpot_prob_each": JACKPOT_PROB_EACH,
    }


def normalize_pool(raw: dict[str, Any] | None) -> dict[str, Any]:
    """校验并补齐奖池字段。"""
    base = default_pool()
    if not raw:
        return base
    costs = raw.get("costs")
    if isinstance(costs, list) and costs:
        base["costs"] = [int(x) for x in costs]
    slots = raw.get("slots")
    if isinstance(slots, list) and slots:
        cleaned: list[dict[str, Any]] = []
        for i, item in enumerate(slots):
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "points")
            is_jackpot = bool(item.get("jackpot")) or kind in (
                "tier_up",
                "jackpot_points",
            )
            cleaned.append(
                {
                    "index": int(item.get("index", i)),
                    "kind": kind,
                    "label": str(item.get("label") or f"奖项{i}"),
                    "points": int(item.get("points") or 0),
                    "weight": int(item.get("weight") or 0),
                    "jackpot": is_jackpot,
                }
            )
        if cleaned:
            base["slots"] = cleaned
    if raw.get("jackpot_prob_each") is not None:
        base["jackpot_prob_each"] = float(raw["jackpot_prob_each"])
    return base


async def _read_json(session: AsyncSession, key: str) -> dict[str, Any] | None:
    row = await session.get(AppSetting, key)
    if row is None or not row.value:
        return None
    try:
        parsed = json.loads(row.value)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


async def _write_json(session: AsyncSession, key: str, value: dict[str, Any]) -> None:
    text = json.dumps(value, ensure_ascii=False)
    row = await session.get(AppSetting, key)
    if row is None:
        session.add(AppSetting(key=key, value=text))
    else:
        row.value = text


async def _read_period(session: AsyncSession) -> str:
    row = await session.get(AppSetting, KEY_PERIOD)
    return (row.value if row else "") or ""


async def _write_period(session: AsyncSession, period_ym: str) -> None:
    row = await session.get(AppSetting, KEY_PERIOD)
    if row is None:
        session.add(AppSetting(key=KEY_PERIOD, value=period_ym))
    else:
        row.value = period_ym


async def ensure_period_pool(
    session: AsyncSession, period_ym: str
) -> tuple[dict[str, Any], bool]:
    """
    确保当前自然月奖池已激活。
    跨月时：若有「下月配置」则晋升为当前，否则沿用上月/默认；下月槽同步为当前副本。
    返回 (奖池, 是否发生跨月晋升，调用方需 commit)。
    """
    active = await _read_period(session)
    if active == period_ym:
        current = normalize_pool(await _read_json(session, KEY_CURRENT))
        return current, False

    pending = await _read_json(session, KEY_NEXT)
    if pending:
        current = normalize_pool(pending)
    else:
        prev = await _read_json(session, KEY_CURRENT)
        current = normalize_pool(prev)

    await _write_json(session, KEY_CURRENT, current)
    await _write_json(session, KEY_NEXT, deepcopy(current))
    await _write_period(session, period_ym)
    await session.flush()
    return current, True


async def get_current_pool(
    session: AsyncSession,
    period_ym: str,
    *,
    commit_if_rolled: bool = True,
) -> dict[str, Any]:
    """
    读取本月奖池。
    commit_if_rolled=False 用于抽奖事务内：只 flush，避免提前 commit 释放行锁。
    """
    pool, rolled = await ensure_period_pool(session, period_ym)
    if rolled and commit_if_rolled:
        await session.commit()
    return pool


async def get_next_pool(session: AsyncSession, period_ym: str) -> dict[str, Any]:
    """读取下月奖池（会顺带 ensure 本月周期）。"""
    await get_current_pool(session, period_ym, commit_if_rolled=True)
    nxt = await _read_json(session, KEY_NEXT)
    return normalize_pool(nxt)


async def save_next_pool(
    session: AsyncSession, period_ym: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """管理端保存下月奖池（本月不生效）；不 commit。"""
    await ensure_period_pool(session, period_ym)
    pool = normalize_pool(payload)
    await _write_json(session, KEY_NEXT, pool)
    await session.flush()
    return pool
