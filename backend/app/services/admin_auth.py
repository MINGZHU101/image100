"""管理员账号：登录、查库、改密、创建。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin
from app.security import hash_password, verify_password
from app.services import audit as audit_service


class InvalidAdminCredentials(Exception):
    pass


class AdminTaken(Exception):
    pass


class PasswordMismatch(Exception):
    pass


async def authenticate(session: AsyncSession, username: str, password: str) -> Admin:
    admin = await session.scalar(select(Admin).where(Admin.username == username.strip()))
    if admin is None or not verify_password(password, admin.password_hash):
        raise InvalidAdminCredentials
    return admin


async def get_by_id(session: AsyncSession, admin_id: uuid.UUID) -> Admin | None:
    return await session.get(Admin, admin_id)


async def list_admins(session: AsyncSession) -> list[Admin]:
    result = await session.execute(select(Admin).order_by(Admin.created_at.asc()))
    return list(result.scalars().all())


async def create_admin(
    session: AsyncSession,
    actor: Admin,
    *,
    username: str,
    password: str,
    display_name: str,
) -> Admin:
    admin = Admin(
        id=uuid.uuid4(),
        username=username.strip(),
        password_hash=hash_password(password),
        display_name=(display_name.strip() or username.strip())[:64],
    )
    session.add(admin)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AdminTaken from exc
    await audit_service.write(
        session,
        actor,
        action="admin.create",
        target_type="admin",
        target_id=str(admin.id),
        detail=f"创建管理员 {admin.username}",
    )
    await session.commit()
    await session.refresh(admin)
    return admin


async def change_password(
    session: AsyncSession,
    admin: Admin,
    *,
    old_password: str,
    new_password: str,
    new_password_confirm: str,
) -> None:
    if new_password != new_password_confirm:
        raise PasswordMismatch
    if not verify_password(old_password, admin.password_hash):
        raise InvalidAdminCredentials
    admin.password_hash = hash_password(new_password)
    await audit_service.write(
        session,
        admin,
        action="admin.change_password",
        target_type="admin",
        target_id=str(admin.id),
        detail="修改自己的密码",
    )
    await session.commit()
