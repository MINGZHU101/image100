"""管理端：用户列表、调分/余额、冻结、强制下线。"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin, PointLedger, User, WalletLedger
from app.services import audit as audit_service
from app.services import points as points_service
from app.services import wallet as wallet_service


async def list_users(
    session: AsyncSession,
    *,
    q: str | None = None,
    member_tier: str | None = None,
    frozen: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[User], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if q:
        like = f"%{q.strip()}%"
        cond = or_(User.username.ilike(like), User.display_name.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if member_tier:
        stmt = stmt.where(User.member_tier == member_tier)
        count_stmt = count_stmt.where(User.member_tier == member_tier)
    if frozen is not None:
        stmt = stmt.where(User.is_frozen.is_(frozen))
        count_stmt = count_stmt.where(User.is_frozen.is_(frozen))

    total = int(await session.scalar(count_stmt) or 0)
    result = await session.execute(
        stmt.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    return user


async def adjust_points(
    session: AsyncSession,
    admin: Admin,
    user: User,
    *,
    delta: int,
    remark: str,
) -> User:
    if delta > 0:
        await points_service.credit(
            session, user, amount=delta, kind="admin_adjust", remark=remark
        )
    else:
        need = abs(delta)
        if user.points_balance < need:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"积分不足，当前 {user.points_balance}",
            )
        user.points_balance = int(user.points_balance) - need
        ledger = PointLedger(
            user_id=user.id,
            delta=-need,
            balance_after=user.points_balance,
            kind="admin_adjust",
            remark=remark,
        )
        session.add(ledger)
    await audit_service.write(
        session,
        admin,
        action="user.adjust_points",
        target_type="user",
        target_id=str(user.id),
        detail=f"{user.username} delta={delta} {remark}",
    )
    await session.commit()
    await session.refresh(user)
    return user


async def adjust_wallet(
    session: AsyncSession,
    admin: Admin,
    user: User,
    *,
    delta: int,
    remark: str,
) -> User:
    if delta > 0:
        await wallet_service.credit_wallet(
            session, user, amount=delta, kind="admin_adjust", remark=remark
        )
    else:
        need = abs(delta)
        if int(user.wallet_balance or 0) < need:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"余额不足，当前 ¥{user.wallet_balance}",
            )
        await wallet_service.debit_wallet(
            session, user, amount=need, kind="admin_adjust", remark=remark
        )
    await audit_service.write(
        session,
        admin,
        action="user.adjust_wallet",
        target_type="user",
        target_id=str(user.id),
        detail=f"{user.username} delta={delta} {remark}",
    )
    await session.commit()
    await session.refresh(user)
    return user


async def set_frozen(
    session: AsyncSession,
    admin: Admin,
    user: User,
    *,
    frozen: bool,
) -> User:
    user.is_frozen = frozen
    if frozen:
        user.token_version = int(user.token_version or 0) + 1
    await audit_service.write(
        session,
        admin,
        action="user.freeze" if frozen else "user.unfreeze",
        target_type="user",
        target_id=str(user.id),
        detail=user.username,
    )
    await session.commit()
    await session.refresh(user)
    return user


async def force_logout(session: AsyncSession, admin: Admin, user: User) -> User:
    user.token_version = int(user.token_version or 0) + 1
    await audit_service.write(
        session,
        admin,
        action="user.force_logout",
        target_type="user",
        target_id=str(user.id),
        detail=user.username,
    )
    await session.commit()
    await session.refresh(user)
    return user


async def export_users_csv(
    session: AsyncSession,
    *,
    q: str | None = None,
    member_tier: str | None = None,
    frozen: bool | None = None,
) -> str:
    users, _ = await list_users(
        session, q=q, member_tier=member_tier, frozen=frozen, page=1, page_size=10000
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "account",
            "display_name",
            "member_tier",
            "wallet_balance",
            "points_balance",
            "is_frozen",
            "newbie_gift_claimed",
            "created_at",
        ]
    )
    for u in users:
        writer.writerow(
            [
                u.username,
                u.display_name,
                u.member_tier,
                u.wallet_balance,
                u.points_balance,
                u.is_frozen,
                u.newbie_gift_claimed,
                u.created_at.isoformat() if u.created_at else "",
            ]
        )
    return buf.getvalue()


async def dashboard_stats(session: AsyncSession) -> dict:
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from app.models.agent_run import AgentRun
    from app.models.generation_run import GenerationRun
    from app.services.quota import shanghai_today_date

    today = shanghai_today_date()
    today_start = datetime.combine(today, datetime.min.time()).replace(
        tzinfo=ZoneInfo("Asia/Shanghai")
    )
    day_ago = datetime.now(ZoneInfo("Asia/Shanghai")) - timedelta(hours=24)

    users_total = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    today_register = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.created_at >= today_start)
        )
        or 0
    )
    today_checkin = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.last_checkin_date == today)
        )
        or 0
    )
    gift_claimed = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.newbie_gift_claimed.is_(True))
        )
        or 0
    )
    gift_unclaimed = int(
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.newbie_gift_claimed.is_(False), User.username != "demo")
        )
        or 0
    )

    points_in = int(
        await session.scalar(
            select(func.coalesce(func.sum(PointLedger.delta), 0)).where(PointLedger.delta > 0)
        )
        or 0
    )
    points_out = int(
        await session.scalar(
            select(func.coalesce(func.sum(PointLedger.delta), 0)).where(PointLedger.delta < 0)
        )
        or 0
    )
    wallet_in = int(
        await session.scalar(
            select(func.coalesce(func.sum(WalletLedger.delta), 0)).where(
                WalletLedger.kind == "mock_recharge"
            )
        )
        or 0
    )

    agent_today = int(
        await session.scalar(
            select(func.count()).select_from(AgentRun).where(AgentRun.created_at >= today_start)
        )
        or 0
    )
    gen_today = int(
        await session.scalar(
            select(func.count())
            .select_from(GenerationRun)
            .where(GenerationRun.created_at >= today_start)
        )
        or 0
    )
    fail_24h = int(
        await session.scalar(
            select(func.count())
            .select_from(AgentRun)
            .where(AgentRun.created_at >= day_ago, AgentRun.status == "failed")
        )
        or 0
    ) + int(
        await session.scalar(
            select(func.count())
            .select_from(GenerationRun)
            .where(GenerationRun.created_at >= day_ago, GenerationRun.status == "failed")
        )
        or 0
    )

    return {
        "users_total": users_total,
        "today_register": today_register,
        "today_checkin": today_checkin,
        "today_ai_runs": agent_today + gen_today,
        "points_credited_total": points_in,
        "points_debited_total": abs(points_out),
        "wallet_recharge_total": wallet_in,
        "newbie_gift_claimed": gift_claimed,
        "newbie_gift_unclaimed": gift_unclaimed,
        "failures_24h": fail_24h,
    }
