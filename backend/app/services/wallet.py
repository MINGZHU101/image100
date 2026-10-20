"""账户余额：入账、扣款、流水。"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.wallet_ledger import WalletLedger


async def credit_wallet(
    session: AsyncSession,
    user: User,
    *,
    amount: int,
    kind: str,
    remark: str = "",
) -> WalletLedger:
    if amount <= 0:
        raise ValueError("入账金额必须为正")
    user.wallet_balance = int(user.wallet_balance or 0) + amount
    ledger = WalletLedger(
        user_id=user.id,
        delta=amount,
        balance_after=user.wallet_balance,
        kind=kind,
        remark=remark,
    )
    session.add(ledger)
    return ledger


async def debit_wallet(
    session: AsyncSession,
    user: User,
    *,
    amount: int,
    kind: str,
    remark: str = "",
) -> WalletLedger:
    if amount <= 0:
        raise ValueError("扣款金额必须为正")
    balance = int(user.wallet_balance or 0)
    if balance < amount:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"余额不足：需要 ¥{amount}，当前 ¥{balance}",
        )
    user.wallet_balance = balance - amount
    ledger = WalletLedger(
        user_id=user.id,
        delta=-amount,
        balance_after=user.wallet_balance,
        kind=kind,
        remark=remark,
    )
    session.add(ledger)
    return ledger


async def list_ledger(
    session: AsyncSession,
    user_id,
    *,
    limit: int = 50,
) -> list[WalletLedger]:
    result = await session.execute(
        select(WalletLedger)
        .where(WalletLedger.user_id == user_id)
        .order_by(WalletLedger.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
