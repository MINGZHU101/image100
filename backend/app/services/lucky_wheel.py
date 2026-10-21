"""幸运大转盘：状态、抽奖、弹幕与管理端记录。"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.membership_rules import MEMBER_TIERS, next_tier_progress, tier_for_spent
from app.models import User
from app.models.lucky_wheel import LuckyWheelSpin
from app.services import app_settings as settings_service
from app.services import lucky_wheel_config as pool_config
from app.services import points as points_service
from app.services import wallet as wallet_service

SHANGHAI = ZoneInfo("Asia/Shanghai")


def now_shanghai() -> datetime:
    return datetime.now(SHANGHAI)


def current_period_ym(now: datetime | None = None) -> str:
    stamp = now or now_shanghai()
    return stamp.strftime("%Y-%m")


def month_end_countdown(now: datetime | None = None) -> dict[str, int]:
    """距下月 1 日 0 点（上海）的天/时/分。"""
    stamp = now or now_shanghai()
    if stamp.month == 12:
        next_month = stamp.replace(
            year=stamp.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    else:
        next_month = stamp.replace(
            month=stamp.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    delta = next_month - stamp
    total_seconds = max(0, int(delta.total_seconds()))
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    return {"days": days, "hours": hours, "minutes": minutes, "total_seconds": total_seconds}


def mask_display_name(name: str) -> str:
    text = (name or "").strip()
    if not text:
        return "用户**"
    return text[0] + "**"


def _slot_is_jackpot(slot: dict[str, Any]) -> bool:
    return bool(slot.get("jackpot")) or slot.get("kind") in (
        "tier_up",
        "jackpot_points",
    )


def build_probabilities(
    slots: list[dict[str, Any]], drawn: set[int], jackpot_prob_each: float
) -> list[tuple[int, float]]:
    """
    初始权重：大奖各 jackpot_prob_each，积分格按 weight 分剩余；
    已抽中归零后在剩余格上重新归一化。
    """
    remaining = [s for s in slots if int(s["index"]) not in drawn]
    if not remaining:
        return []

    jackpots = [s for s in remaining if _slot_is_jackpot(s)]
    points = [s for s in remaining if not _slot_is_jackpot(s)]
    jackpot_total = jackpot_prob_each * len(jackpots)
    # 若大奖过多导致超过 1，则整体按比例压缩
    if jackpot_total >= 1.0 and points:
        jackpot_prob_each = (1.0 - 1e-9) / len(jackpots)
        jackpot_total = jackpot_prob_each * len(jackpots)
    elif jackpot_total >= 1.0:
        jackpot_prob_each = 1.0 / len(jackpots)
        jackpot_total = 1.0

    rest = max(0.0, 1.0 - jackpot_total)
    weight_sum = sum(max(0, int(s.get("weight") or 0)) for s in points) or 1

    raw: list[tuple[int, float]] = []
    for s in jackpots:
        raw.append((int(s["index"]), jackpot_prob_each))
    for s in points:
        w = max(0, int(s.get("weight") or 0))
        raw.append((int(s["index"]), rest * (w / weight_sum)))

    total = sum(p for _, p in raw) or 1.0
    return [(idx, p / total) for idx, p in raw]


def pick_slot(probs: list[tuple[int, float]]) -> int:
    r = random.random()
    acc = 0.0
    for idx, p in probs:
        acc += p
        if r <= acc:
            return idx
    return probs[-1][0]


async def _user_spins(
    session: AsyncSession, user_id, period_ym: str
) -> list[LuckyWheelSpin]:
    result = await session.execute(
        select(LuckyWheelSpin)
        .where(
            LuckyWheelSpin.user_id == user_id,
            LuckyWheelSpin.period_ym == period_ym,
        )
        .order_by(LuckyWheelSpin.spin_index.asc())
    )
    return list(result.scalars().all())


async def get_state(session: AsyncSession, user: User) -> dict[str, Any]:
    period = current_period_ym()
    pool = await pool_config.get_current_pool(session, period)
    spins = await _user_spins(session, user.id, period)
    drawn = {s.slot_index for s in spins}
    spin_count = len(spins)
    costs: list[int] = list(pool["costs"])
    exhausted = spin_count >= len(costs) or len(drawn) >= len(pool["slots"])
    next_cost = None if exhausted else int(costs[spin_count])
    slots_out = []
    for slot in pool["slots"]:
        idx = int(slot["index"])
        slots_out.append(
            {
                "index": idx,
                "kind": slot["kind"],
                "label": slot["label"],
                "points": int(slot.get("points") or 0),
                "jackpot": _slot_is_jackpot(slot),
                "drawn": idx in drawn,
            }
        )
    return {
        "period_ym": period,
        "countdown": month_end_countdown(),
        "wallet_balance": int(user.wallet_balance or 0),
        "points_balance": int(user.points_balance or 0),
        "member_tier": user.member_tier,
        "spin_count": spin_count,
        "max_spins": len(costs),
        "next_cost_yuan": next_cost,
        "exhausted": exhausted,
        "slots": slots_out,
        "history": [
            {
                "spin_index": s.spin_index,
                "cost_yuan": s.cost_yuan,
                "slot_index": s.slot_index,
                "prize_kind": s.prize_kind,
                "prize_label": s.prize_label,
                "points_awarded": s.points_awarded,
                "is_jackpot": s.is_jackpot,
                "created_at": s.created_at.isoformat(),
            }
            for s in spins
        ],
    }


async def list_barrage(session: AsyncSession, *, limit: int = 10) -> list[dict]:
    """全站大奖弹幕：近 N 条（脱敏）。"""
    result = await session.execute(
        select(LuckyWheelSpin)
        .where(LuckyWheelSpin.is_jackpot.is_(True))
        .order_by(LuckyWheelSpin.created_at.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    return [
        {
            "masked_name": mask_display_name(r.display_name_snapshot),
            "prize_label": r.prize_label,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


async def _apply_tier_up(session: AsyncSession, user: User) -> tuple[int, str]:
    """
    提升一级：补足到下一档累计消耗门槛；已是钻石则发 15000 积分。
    返回 (入账积分, 说明)。
    """
    next_name, need = next_tier_progress(int(user.points_spent_total or 0))
    if next_name is None:
        amount = pool_config.DIAMOND_TIER_UP_POINTS
        await points_service.credit(
            session,
            user,
            amount=amount,
            kind="lucky_wheel",
            remark="幸运大转盘·钻石升档折现",
        )
        return amount, f"已是最高等级，折现 {amount} 积分"

    user.points_spent_total = int(user.points_spent_total or 0) + int(need)
    user.member_tier = tier_for_spent(user.points_spent_total)
    return 0, f"会员升至 {user.member_tier}（累计消耗补足 {need}）"


async def spin(session: AsyncSession, user: User, *, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先确认抽奖")

    # 行锁，避免并发连抽
    locked = await session.execute(
        select(User).where(User.id == user.id).with_for_update()
    )
    user = locked.scalar_one()

    period = current_period_ym()
    pool = await pool_config.get_current_pool(session, period)
    spins = await _user_spins(session, user.id, period)
    drawn = {s.slot_index for s in spins}
    spin_count = len(spins)
    costs: list[int] = list(pool["costs"])

    if spin_count >= len(costs) or len(drawn) >= len(pool["slots"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "本月奖池已抽完，下月重置")

    cost = int(costs[spin_count])
    if int(user.wallet_balance or 0) < cost:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"余额不足：需要 ¥{cost}，当前 ¥{user.wallet_balance}，请先充值",
        )

    probs = build_probabilities(
        pool["slots"], drawn, float(pool.get("jackpot_prob_each") or 0.02)
    )
    if not probs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "本月奖池已抽完，下月重置")

    chosen_index = pick_slot(probs)
    slot_map = {int(s["index"]): s for s in pool["slots"]}
    slot = slot_map[chosen_index]
    is_jackpot = _slot_is_jackpot(slot)

    await wallet_service.debit_wallet(
        session,
        user,
        amount=cost,
        kind="lucky_wheel",
        remark=f"幸运大转盘第 {spin_count + 1} 次",
    )

    # 余额消耗按汇率计入累计消耗并结算等级
    rate = await settings_service.points_per_yuan(session)
    spent_add = cost * max(1, rate)
    user.points_spent_total = int(user.points_spent_total or 0) + spent_add
    user.member_tier = tier_for_spent(user.points_spent_total)

    points_awarded = 0
    remark = ""
    kind = str(slot["kind"])
    label = str(slot["label"])

    if kind == "tier_up":
        points_awarded, remark = await _apply_tier_up(session, user)
    elif int(slot.get("points") or 0) > 0:
        points_awarded = int(slot["points"])
        await points_service.credit(
            session,
            user,
            amount=points_awarded,
            kind="lucky_wheel",
            remark=f"幸运大转盘·{label}",
        )
        remark = f"获得 {points_awarded} 积分"
    else:
        remark = label

    name = (user.display_name or user.username or "").strip()
    record = LuckyWheelSpin(
        user_id=user.id,
        period_ym=period,
        spin_index=spin_count + 1,
        cost_yuan=cost,
        slot_index=chosen_index,
        prize_kind=kind,
        prize_label=label,
        points_awarded=points_awarded,
        is_jackpot=is_jackpot,
        display_name_snapshot=name,
        remark=remark,
    )
    session.add(record)
    await session.commit()
    await session.refresh(user)
    await session.refresh(record)

    state = await get_state(session, user)
    return {
        "result": {
            "spin_index": record.spin_index,
            "cost_yuan": record.cost_yuan,
            "slot_index": record.slot_index,
            "prize_kind": record.prize_kind,
            "prize_label": record.prize_label,
            "points_awarded": record.points_awarded,
            "is_jackpot": record.is_jackpot,
            "remark": record.remark,
            "member_tier": user.member_tier,
            "wallet_balance": int(user.wallet_balance or 0),
            "points_balance": int(user.points_balance or 0),
        },
        "state": state,
    }


async def admin_list_spins(
    session: AsyncSession,
    *,
    q: str | None,
    period_ym: str | None,
    jackpot_only: bool,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    stmt: Select = (
        select(LuckyWheelSpin, User)
        .join(User, User.id == LuckyWheelSpin.user_id)
        .order_by(LuckyWheelSpin.created_at.desc())
    )
    count_stmt = (
        select(func.count())
        .select_from(LuckyWheelSpin)
        .join(User, User.id == LuckyWheelSpin.user_id)
    )
    if period_ym:
        stmt = stmt.where(LuckyWheelSpin.period_ym == period_ym)
        count_stmt = count_stmt.where(LuckyWheelSpin.period_ym == period_ym)
    if jackpot_only:
        stmt = stmt.where(LuckyWheelSpin.is_jackpot.is_(True))
        count_stmt = count_stmt.where(LuckyWheelSpin.is_jackpot.is_(True))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (User.username.ilike(like)) | (User.display_name.ilike(like))
        )
        count_stmt = count_stmt.where(
            (User.username.ilike(like)) | (User.display_name.ilike(like))
        )

    total = int(await session.scalar(count_stmt) or 0)
    result = await session.execute(
        stmt.offset((page - 1) * page_size).limit(page_size)
    )
    items: list[dict] = []
    for spin_row, u in result.all():
        items.append(
            {
                "id": str(spin_row.id),
                "account": u.username,
                "display_name": u.display_name or "",
                "period_ym": spin_row.period_ym,
                "spin_index": spin_row.spin_index,
                "cost_yuan": spin_row.cost_yuan,
                "slot_index": spin_row.slot_index,
                "prize_kind": spin_row.prize_kind,
                "prize_label": spin_row.prize_label,
                "points_awarded": spin_row.points_awarded,
                "is_jackpot": spin_row.is_jackpot,
                "remark": spin_row.remark or "",
                "created_at": spin_row.created_at.isoformat(),
            }
        )
    return items, total


async def admin_get_config(session: AsyncSession) -> dict[str, Any]:
    period = current_period_ym()
    current = await pool_config.get_current_pool(session, period)
    nxt = await pool_config.get_next_pool(session, period)
    return {
        "period_ym": period,
        "current": current,
        "next": nxt,
        "tiers": list(MEMBER_TIERS),
        "note": "修改 next 将于下月 1 日生效；当前月奖池不受影响。",
    }


async def admin_save_next_config(
    session: AsyncSession, payload: dict[str, Any]
) -> dict[str, Any]:
    """保存下月配置；不 commit，由路由统一提交。"""
    period = current_period_ym()
    saved = await pool_config.save_next_pool(session, period, payload)
    return {
        "period_ym": period,
        "next": saved,
        "message": "已保存，下月生效",
    }
