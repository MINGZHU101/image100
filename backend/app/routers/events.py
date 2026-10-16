"""SSE：按 run_id 推送工具进度。"""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.deps import DbDep
from app.events import subscribe_events
from app.models.tool_run import ToolRun

router = APIRouter(tags=["events"])


@router.get("/events/{run_id}")
async def stream_run_events(run_id: UUID, db: DbDep) -> StreamingResponse:
    """
    Server-Sent Events。
    若 run 已结束，立即推送终态并关闭；否则订阅 Redis 直到 completed/error。
    """
    run = await db.get(ToolRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行不存在")


    async def event_generator():
        # 已结束：直接回放终态，避免错过事件
        if run is not None and run.status in ("succeeded", "failed"):
            if run.status == "succeeded":
                payload = {
                    "run_id": str(run.id),
                    "session_id": str(run.session_id),
                    "asset_id": str(run.result_asset_id) if run.result_asset_id else None,
                }
                yield _sse("completed", payload)
            else:
                yield _sse(
                    "error",
                    {"run_id": str(run.id), "message": run.error or "failed"},
                )
            return

        # 心跳 + 订阅；终态后结束
        queue: asyncio.Queue = asyncio.Queue()

        async def reader():
            async for payload in subscribe_events(run_id):
                await queue.put(payload)

        task = asyncio.create_task(reader())
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    # 注释：保持连接，防止代理超时
                    yield ": keepalive\n\n"
                    continue

                event_name = str(payload.get("event") or "message")
                yield _sse(event_name, payload)
                if event_name in ("completed", "error"):
                    break
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
