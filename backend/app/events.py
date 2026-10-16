"""Redis Pub/Sub：工具运行进度事件。"""

import json
from uuid import UUID

from redis.asyncio import Redis

from app.config import get_settings


def channel_for_run(run_id: UUID | str) -> str:
    return f"image100:run:{run_id}"


async def publish_event(run_id: UUID | str, payload: dict) -> None:
    """向指定 run 频道发布 JSON 事件。"""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.publish(channel_for_run(run_id), json.dumps(payload, ensure_ascii=False))
    finally:
        await client.aclose()


async def subscribe_events(run_id: UUID | str):
    """异步生成器：订阅并 yield 事件 dict。"""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(channel_for_run(run_id))
    try:
        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, str):
                yield json.loads(data)
    finally:
        await pubsub.unsubscribe(channel_for_run(run_id))
        await pubsub.aclose()
        await client.aclose()
