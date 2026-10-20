"""积分入账、扣减与流水。"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.membership_rules import tier_for_spent
from app.models import User
from app.models.point_ledger import PointLedger
from app.services import auth as auth_service


class InsufficientPoints(Exception):
    def __init__(self, need: int, balance: int) -> None:
        self.need = need
        self.balance = balance
        super().__init__(f"积分不足：需要 {need}，当前 {balance}")


async def credit(
    session: AsyncSession,
    user: User,
    *,
    amount: int,
    kind: str,
    remark: str = "",
) -> PointLedger:
    """入账（正数）。调用方负责 commit（注册场景可先 flush）。"""
    if amount <= 0:
        raise ValueError("入账金额必须为正")
    user.points_balance = int(user.points_balance) + amount
    ledger = PointLedger(
        user_id=user.id,
        delta=amount,
        balance_after=user.points_balance,
        kind=kind,
        remark=remark,
    )
    session.add(ledger)
    return ledger


async def debit(
    session: AsyncSession,
    user: User,
    *,
    amount: int,
    kind: str,
    remark: str = "",
) -> PointLedger | None:
    """扣减积分并累计消耗、结算会员等级。demo 用户跳过扣减。"""
    if amount < 0:
        raise ValueError("扣减金额不能为负")
    if amount == 0:
        return None
    if auth_service.is_demo_user(user):
        return None
    if user.points_balance < amount:
        raise InsufficientPoints(amount, user.points_balance)

    user.points_balance = int(user.points_balance) - amount
    user.points_spent_total = int(user.points_spent_total) + amount
    user.member_tier = tier_for_spent(user.points_spent_total)
    ledger = PointLedger(
        user_id=user.id,
        delta=-amount,
        balance_after=user.points_balance,
        kind=kind,
        remark=remark,
    )
    session.add(ledger)
    return ledger


def raise_insufficient(exc: InsufficientPoints) -> None:
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": "POINTS_INSUFFICIENT",
            "message": str(exc),
            "need": exc.need,
            "balance": exc.balance,
        },
    )


async def list_ledger(
    session: AsyncSession,
    user_id,
    *,
    limit: int = 50,
) -> list[PointLedger]:
    result = await session.execute(
        select(PointLedger)
        .where(PointLedger.user_id == user_id)
        .order_by(PointLedger.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
