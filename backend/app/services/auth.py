"""注册 / 登录 / 查用户。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.membership_rules import DEMO_ACCOUNT, REGISTER_BONUS
from app.models import User
from app.security import hash_password, verify_password
from app.services import points as points_service


class AccountTaken(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class PasswordMismatch(Exception):
    pass


async def register(
    session: AsyncSession,
    *,
    account: str,
    display_name: str,
    password: str,
    password_confirm: str,
) -> User:
    if password != password_confirm:
        raise PasswordMismatch
    user = User(
        username=account.strip(),
        display_name=display_name.strip() or account.strip(),
        password_hash=hash_password(password),
        member_tier="青铜",
        points_balance=0,
        points_spent_total=0,
        invite_reward_claimed=False,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AccountTaken from exc

    await points_service.credit(
        session,
        user,
        amount=REGISTER_BONUS,
        kind="register_bonus",
        remark="注册赠送",
    )
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, account: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.username == account.strip()))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials
    return user


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_account(session: AsyncSession, account: str) -> User | None:
    return await session.scalar(select(User).where(User.username == account.strip()))


def is_demo_user(user: User) -> bool:
    return user.username == DEMO_ACCOUNT


async def change_password(
    session: AsyncSession,
    user: User,
    *,
    old_password: str,
    new_password: str,
    new_password_confirm: str,
) -> None:
    if new_password != new_password_confirm:
        raise PasswordMismatch
    if not verify_password(old_password, user.password_hash):
        raise InvalidCredentials
    user.password_hash = hash_password(new_password)
    await session.commit()


async def update_display_name(session: AsyncSession, user: User, display_name: str) -> User:
    cleaned = display_name.strip()
    if not cleaned:
        raise ValueError("用户名不能为空")
    user.display_name = cleaned[:64]
    await session.commit()
    await session.refresh(user)
    return user
