"""批量生成演示用户，让管理端仪表盘有数据可看。

用法（在 backend 目录、image100 环境）：
  python -m scripts.seed_demo_users
  python -m scripts.seed_demo_users --count 500

说明：
- 登录账号 username 库内唯一（seed_u0001…）；已存在则跳过
- 展示名 display_name 故意重复若干个（如「张三」「李四」）
- 统一密码：Seed123456
"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import SessionFactory
from app.membership_rules import tier_for_spent
from app.models import PointLedger, User, WalletLedger
from app.models.generation_run import GenerationRun
from app.security import hash_password

SHANGHAI = ZoneInfo("Asia/Shanghai")
DEFAULT_PASSWORD = "Seed123456"
PREFIX = "seed_u"

DISPLAY_POOL = [
    "张三",
    "李四",
    "王五",
    "赵六",
    "小明",
    "小红",
    "阿强",
    "阿美",
    "测试用户",
    "演示账号",
    "电商达人",
    "视觉设计师",
]


@dataclass
class PlannedUser:
    user: User
    gift_claimed: bool
    gift_points: int
    debit: int
    wallet: int


def _spent_for_tier_mix(i: int) -> int:
    bucket = i % 10
    if bucket == 0:
        return random.randint(15_000, 25_000)
    if bucket <= 2:
        return random.randint(5_000, 14_999)
    if bucket <= 4:
        return random.randint(2_000, 4_999)
    if bucket <= 6:
        return random.randint(500, 1_999)
    return random.randint(0, 499)


async def seed(count: int) -> None:
    password_hash = hash_password(DEFAULT_PASSWORD)
    now = datetime.now(SHANGHAI)
    today = now.date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=SHANGHAI)

    created = 0
    skipped = 0
    planned: list[PlannedUser] = []

    async with SessionFactory() as session:
        existing = set(
            (
                await session.execute(
                    select(User.username).where(User.username.like(f"{PREFIX}%"))
                )
            )
            .scalars()
            .all()
        )

        # 第一阶段：只插用户，保证外键可引用
        for i in range(1, count + 1):
            username = f"{PREFIX}{i:04d}"
            if username in existing:
                skipped += 1
                continue

            spent = _spent_for_tier_mix(i)
            if i % 7 == 0:
                created_at = today_start + timedelta(
                    hours=random.randint(0, max(0, now.hour)),
                    minutes=random.randint(0, 59),
                )
            else:
                created_at = now - timedelta(days=random.randint(1, 90))

            last_checkin = (
                today
                if i % 4 == 0
                else (today - timedelta(days=random.randint(1, 10)) if i % 3 == 0 else None)
            )
            gift_claimed = i % 5 != 0
            points = random.randint(50, 8000) if gift_claimed else random.randint(0, 200)
            wallet = random.randint(0, 500) if i % 3 == 0 else random.randint(0, 50)
            gift_points = random.choice([1000, 2000, 2000, 3000]) if gift_claimed else 0
            debit = (
                min(spent, random.randint(50, 500))
                if points > 100 and spent > 0
                else 0
            )

            user = User(
                id=uuid.uuid4(),
                username=username,
                display_name=DISPLAY_POOL[i % len(DISPLAY_POOL)],
                password_hash=password_hash,
                member_tier=tier_for_spent(spent),
                wallet_balance=wallet,
                points_balance=points,
                points_spent_total=spent,
                last_checkin_date=last_checkin,
                newbie_gift_claimed=gift_claimed,
                invite_reward_claimed=i % 11 == 0,
                is_frozen=i % 47 == 0,
                token_version=0,
            )
            user.created_at = created_at
            session.add(user)
            planned.append(
                PlannedUser(
                    user=user,
                    gift_claimed=gift_claimed,
                    gift_points=gift_points,
                    debit=debit,
                    wallet=wallet if i % 3 == 0 and wallet > 0 else 0,
                )
            )
            created += 1

        await session.flush()

        # 第二阶段：流水（用户已落库）
        for item in planned:
            u = item.user
            if item.gift_claimed and item.gift_points > 0:
                session.add(
                    PointLedger(
                        user_id=u.id,
                        delta=item.gift_points,
                        balance_after=u.points_balance,
                        kind="newbie_gift",
                        remark="种子数据·新手礼包",
                    )
                )
            if item.debit > 0:
                session.add(
                    PointLedger(
                        user_id=u.id,
                        delta=-item.debit,
                        balance_after=max(0, u.points_balance - 10),
                        kind="consume_generation",
                        remark="种子数据·文生图消耗",
                    )
                )
            if item.wallet > 0:
                session.add(
                    WalletLedger(
                        user_id=u.id,
                        delta=item.wallet,
                        balance_after=item.wallet,
                        kind="mock_recharge",
                        remark="种子数据·模拟充值",
                    )
                )

        # 今日 AI / 失败统计
        sample = [p.user for p in planned[: min(80, len(planned))]]
        for idx, user in enumerate(sample):
            status = "failed" if idx % 5 == 0 else "succeeded"
            run = GenerationRun(
                owner_id=user.id,
                prompt=f"种子文生图 #{idx}",
                params={"seed": True},
                image_provider="mock",
                status=status,
                progress=100 if status == "succeeded" else 40,
                result_asset_ids=[],
                error="seed mock failure" if status == "failed" else None,
                finished_at=now if status == "succeeded" else None,
            )
            run.created_at = today_start + timedelta(minutes=idx * 3)
            session.add(run)

        await session.commit()

    print(
        f"完成：新建 {created}，跳过已存在 {skipped}，目标 {count}。"
        f"密码统一为 {DEFAULT_PASSWORD}；展示名在池内重复。"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="种子演示用户")
    parser.add_argument("--count", type=int, default=500)
    args = parser.parse_args()
    asyncio.run(seed(max(1, args.count)))


if __name__ == "__main__":
    main()
