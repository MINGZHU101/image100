"""个人中心：签到、模拟充值、余额兑换积分、头像。"""

from __future__ import annotations

import io
import uuid

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.membership_rules import AVATAR_MAX_BYTES, DEMO_ACCOUNT
from app.models import User
from app.services import app_settings as settings_service
from app.services.points import credit
from app.services.quota import shanghai_today_date
from app.services import wallet as wallet_service
from app.storage import get_storage

_ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def checkin(session: AsyncSession, user: User) -> dict:
    today = shanghai_today_date()
    if user.last_checkin_date == today:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "今日已签到")
    table = await settings_service.checkin_points_table(session)
    amount = int(table.get(user.member_tier, 20))
    await credit(
        session,
        user,
        amount=amount,
        kind="checkin",
        remark=f"每日签到（{user.member_tier}）",
    )
    user.last_checkin_date = today
    await session.commit()
    await session.refresh(user)
    return {"points_gained": amount, "points_balance": user.points_balance, "checkin_date": today.isoformat()}


async def claim_newbie_gift(session: AsyncSession, user: User) -> dict:
    """一次性领取新手礼包积分。demo 与已领用户拒绝。"""
    if user.username == DEMO_ACCOUNT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "演示账号不参与新手礼包")
    if bool(getattr(user, "newbie_gift_claimed", False)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "礼包已领取")
    amount = await settings_service.newbie_gift_points(session)
    await credit(
        session,
        user,
        amount=amount,
        kind="newbie_gift",
        remark="新手礼包",
    )
    user.newbie_gift_claimed = True
    await session.commit()
    await session.refresh(user)
    return {
        "points_gained": amount,
        "points_balance": user.points_balance,
        "newbie_gift_claimed": True,
    }


async def mock_recharge(session: AsyncSession, user: User, yuan: int) -> dict:
    """模拟充值：金额进入账户余额（不直接加积分）。"""
    max_yuan = await settings_service.mock_recharge_max_yuan(session)
    if yuan < 1 or yuan > max_yuan:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"单次充值金额须为 1～{max_yuan} 元",
        )
    await wallet_service.credit_wallet(
        session,
        user,
        amount=yuan,
        kind="mock_recharge",
        remark=f"模拟充值 ¥{yuan}",
    )
    await session.commit()
    await session.refresh(user)
    return {
        "yuan": yuan,
        "wallet_balance": user.wallet_balance,
        "points_balance": user.points_balance,
    }


async def exchange_points(session: AsyncSession, user: User, yuan: int) -> dict:
    """余额兑换积分：汇率取运营配置。"""
    if yuan < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "兑换金额至少 1 元")
    if yuan > int(user.wallet_balance or 0):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"余额不足：当前 ¥{user.wallet_balance}",
        )
    rate = await settings_service.points_per_yuan(session)
    points = yuan * rate
    await wallet_service.debit_wallet(
        session,
        user,
        amount=yuan,
        kind="exchange_points",
        remark=f"兑换积分：¥{yuan} → {points} 积分",
    )
    await credit(
        session,
        user,
        amount=points,
        kind="exchange_from_wallet",
        remark=f"余额兑换：¥{yuan}",
    )
    await session.commit()
    await session.refresh(user)
    return {
        "yuan": yuan,
        "points_gained": points,
        "wallet_balance": user.wallet_balance,
        "points_balance": user.points_balance,
    }


async def upload_avatar(session: AsyncSession, user: User, upload: UploadFile) -> User:
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "头像仅支持 jpeg / png / webp")

    data = await upload.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "空文件")
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "头像不能超过 2MB")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            format_name = (image.format or "PNG").upper()
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无法解析为有效图片") from exc

    ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    ext = ext_map.get(format_name, _ALLOWED_MIME[content_type])
    mime = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[ext]

    avatar_id = uuid.uuid4()
    storage_key = f"avatars/{user.id}/{avatar_id}{ext}"
    get_storage().put(storage_key, data, mime)
    user.avatar_key = storage_key
    await session.commit()
    await session.refresh(user)
    return user
