"""会员等级、签到与配额常量（与 v10 交付说明对齐）。"""

from __future__ import annotations

# 等级从低到高
MEMBER_TIERS: tuple[str, ...] = ("青铜", "白银", "黄金", "铂金", "钻石")

# 累计消耗积分 → 等级
TIER_BY_SPENT: tuple[tuple[int, str], ...] = (
    (15_000, "钻石"),
    (5_000, "铂金"),
    (2_000, "黄金"),
    (500, "白银"),
    (0, "青铜"),
)

# 每日签到积分
CHECKIN_POINTS: dict[str, int] = {
    "青铜": 20,
    "白银": 40,
    "黄金": 60,
    "铂金": 100,
    "钻石": 150,
}

# 每日 AI 次数上限（demo 不限）
DAILY_AI_LIMIT: dict[str, int] = {
    "青铜": 20,
    "白银": 50,
    "黄金": 100,
    "铂金": 200,
    "钻石": 500,
}

# 并发 run 上限
CONCURRENT_RUN_LIMIT: dict[str, int] = {
    "青铜": 1,
    "白银": 2,
    "黄金": 3,
    "铂金": 4,
    "钻石": 5,
}

# AI 操作扣分
COST_AGENT_TURN = 50
COST_GENERATION = 80
COST_CLOUD_EDIT = 60
COST_COPYWRITING = 40

REGISTER_BONUS = 2000
INVITE_REWARD = 200
INVITE_TTL_SECONDS = 600
INVITE_CODE_LENGTH = 5
# 排除易混 0/O/1/I
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

MOCK_RECHARGE_POINTS_PER_YUAN = 10
MOCK_RECHARGE_MAX_YUAN = 1000

AVATAR_MAX_BYTES = 2 * 1024 * 1024

DEMO_ACCOUNT = "demo"


def tier_for_spent(points_spent_total: int) -> str:
    """按累计消耗结算会员等级。"""
    for threshold, tier in TIER_BY_SPENT:
        if points_spent_total >= threshold:
            return tier
    return "青铜"


def next_tier_progress(points_spent_total: int) -> tuple[str | None, int]:
    """返回 (下一档名称, 距下一档还需消耗)；已是钻石则 (None, 0)。"""
    ascending = list(reversed(TIER_BY_SPENT))
    for threshold, tier in ascending:
        if points_spent_total < threshold:
            return tier, threshold - points_spent_total
    return None, 0
