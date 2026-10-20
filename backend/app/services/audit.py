"""管理员操作日志写入。"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin, AuditLog


async def write(
    session: AsyncSession,
    admin: Admin | None,
    *,
    action: str,
    target_type: str = "",
    target_id: str = "",
    detail: str = "",
) -> AuditLog:
    log = AuditLog(
        id=uuid.uuid4(),
        admin_id=admin.id if admin else None,
        admin_username=admin.username if admin else "",
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    session.add(log)
    return log
