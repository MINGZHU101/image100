"""AI 操作计费：配额检查 + 扣积分 + 占用日额度。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services import points as points_service
from app.services import quota as quota_service


async def charge_ai_operation(
    session: AsyncSession,
    user: User,
    *,
    cost: int,
    kind: str,
    remark: str,
) -> None:
    """在创建 AI 任务前调用；失败抛 HTTPException。"""
    await quota_service.ensure_can_start_ai(session, user)
    try:
        await points_service.debit(
            session,
            user,
            amount=cost,
            kind=kind,
            remark=remark,
        )
    except points_service.InsufficientPoints as exc:
        points_service.raise_insufficient(exc)
    await session.commit()
    await quota_service.consume_daily_slot(user)
