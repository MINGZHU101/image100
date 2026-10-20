"""管理端：公告、流水查询、批量发分、会话概览、邀请概览。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Admin,
    Announcement,
    AuditLog,
    EditSession,
    PointLedger,
    User,
    WalletLedger,
)
from app.services import app_settings as settings_service
from app.services import audit as audit_service
from app.services import points as points_service


async def list_point_ledgers(
    session: AsyncSession,
    *,
    q: str | None = None,
    kind: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[PointLedger, str]], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    stmt = select(PointLedger, User.username).join(User, User.id == PointLedger.user_id)
    count_stmt = (
        select(func.count())
        .select_from(PointLedger)
        .join(User, User.id == PointLedger.user_id)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(User.username.ilike(like))
        count_stmt = count_stmt.where(User.username.ilike(like))
    if kind:
        stmt = stmt.where(PointLedger.kind == kind)
        count_stmt = count_stmt.where(PointLedger.kind == kind)
    if since:
        stmt = stmt.where(PointLedger.created_at >= since)
        count_stmt = count_stmt.where(PointLedger.created_at >= since)
    if until:
        stmt = stmt.where(PointLedger.created_at <= until)
        count_stmt = count_stmt.where(PointLedger.created_at <= until)

    total = int(await session.scalar(count_stmt) or 0)
    rows = await session.execute(
        stmt.order_by(PointLedger.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [(row[0], row[1]) for row in rows.all()], total


async def list_wallet_ledgers(
    session: AsyncSession,
    *,
    q: str | None = None,
    kind: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[WalletLedger, str]], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    stmt = select(WalletLedger, User.username).join(User, User.id == WalletLedger.user_id)
    count_stmt = (
        select(func.count())
        .select_from(WalletLedger)
        .join(User, User.id == WalletLedger.user_id)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(User.username.ilike(like))
        count_stmt = count_stmt.where(User.username.ilike(like))
    if kind:
        stmt = stmt.where(WalletLedger.kind == kind)
        count_stmt = count_stmt.where(WalletLedger.kind == kind)

    total = int(await session.scalar(count_stmt) or 0)
    rows = await session.execute(
        stmt.order_by(WalletLedger.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [(row[0], row[1]) for row in rows.all()], total


async def list_invite_claimed(session: AsyncSession, page: int = 1, page_size: int = 20):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    base = select(User).where(User.invite_reward_claimed.is_(True))
    total = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.invite_reward_claimed.is_(True))
        )
        or 0
    )
    result = await session.execute(
        base.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def list_sessions_overview(
    session: AsyncSession,
    *,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    # 按用户聚合会话数
    stmt = (
        select(
            User.id,
            User.username,
            User.display_name,
            func.count(EditSession.id).label("session_count"),
            func.max(EditSession.updated_at).label("last_updated"),
        )
        .outerjoin(EditSession, EditSession.owner_id == User.id)
        .group_by(User.id)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(User.username.ilike(like))

    count_stmt = select(func.count()).select_from(User)
    if q:
        count_stmt = count_stmt.where(User.username.ilike(f"%{q.strip()}%"))
    total = int(await session.scalar(count_stmt) or 0)

    rows = await session.execute(
        stmt.order_by(func.max(EditSession.updated_at).desc().nulls_last())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for row in rows.all():
        items.append(
            {
                "user_id": str(row.id),
                "account": row.username,
                "display_name": row.display_name,
                "session_count": int(row.session_count or 0),
                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
            }
        )
    return items, total


async def list_announcements(session: AsyncSession, *, published_only: bool = False):
    stmt = select(Announcement).order_by(Announcement.created_at.desc())
    if published_only:
        stmt = stmt.where(Announcement.is_published.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def latest_announcement(session: AsyncSession) -> Announcement | None:
    result = await session.execute(
        select(Announcement)
        .where(Announcement.is_published.is_(True))
        .order_by(Announcement.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_announcement(
    session: AsyncSession,
    admin: Admin,
    *,
    title: str,
    body: str,
    is_published: bool,
) -> Announcement:
    row = Announcement(
        id=uuid.uuid4(),
        title=title.strip(),
        body=body or "",
        is_published=is_published,
    )
    session.add(row)
    await audit_service.write(
        session,
        admin,
        action="announcement.create",
        target_type="announcement",
        target_id=str(row.id),
        detail=title,
    )
    await session.commit()
    await session.refresh(row)
    return row


async def update_announcement(
    session: AsyncSession,
    admin: Admin,
    announcement_id: uuid.UUID,
    *,
    title: str | None = None,
    body: str | None = None,
    is_published: bool | None = None,
) -> Announcement:
    row = await session.get(Announcement, announcement_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "公告不存在")
    if title is not None:
        row.title = title.strip()
    if body is not None:
        row.body = body
    if is_published is not None:
        row.is_published = is_published
    await audit_service.write(
        session,
        admin,
        action="announcement.update",
        target_type="announcement",
        target_id=str(row.id),
        detail=row.title,
    )
    await session.commit()
    await session.refresh(row)
    return row


async def list_audit_logs(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[AuditLog], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = int(await session.scalar(select(func.count()).select_from(AuditLog)) or 0)
    result = await session.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def update_settings(
    session: AsyncSession,
    admin: Admin,
    payload: dict,
) -> dict[str, str]:
    updates: dict[str, str] = {}
    for key in (
        "newbie_gift_points",
        "points_per_yuan",
        "mock_recharge_max_yuan",
    ):
        if key in payload and payload[key] is not None:
            updates[key] = str(int(payload[key]))
    for key in ("checkin_points", "daily_ai_limit", "concurrent_run_limit"):
        if key in payload and payload[key] is not None:
            updates[key] = json.dumps(payload[key], ensure_ascii=False)
    result = await settings_service.upsert_many(session, updates)
    await audit_service.write(
        session,
        admin,
        action="settings.update",
        target_type="settings",
        target_id="",
        detail=json.dumps(updates, ensure_ascii=False),
    )
    await session.commit()
    return result


async def batch_grant_points(
    session: AsyncSession,
    admin: Admin,
    *,
    amount: int,
    remark: str,
    accounts: list[str] | None,
) -> dict:
    if accounts:
        names = [a.strip() for a in accounts if a.strip()]
        result = await session.execute(select(User).where(User.username.in_(names)))
        users = list(result.scalars().all())
    else:
        result = await session.execute(select(User).where(User.is_frozen.is_(False)))
        users = list(result.scalars().all())

    granted = 0
    for user in users:
        await points_service.credit(
            session,
            user,
            amount=amount,
            kind="admin_batch",
            remark=remark,
        )
        granted += 1

    await audit_service.write(
        session,
        admin,
        action="points.batch_grant",
        target_type="users",
        target_id="",
        detail=f"amount={amount} count={granted} {remark}",
    )
    await session.commit()
    return {"granted_users": granted, "amount": amount}
