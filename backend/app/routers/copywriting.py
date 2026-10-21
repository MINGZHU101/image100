"""文案生成：分阶段 SSE。"""

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.deps import CurrentUser, DbDep
from app.membership_rules import COST_COPYWRITING
from app.models import User
from app.services import billing
from app.services import copywriting as copywriting_service

router = APIRouter(prefix="/copywriting", tags=["copywriting"])


class CopywritingIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    asset_id: UUID | None = None


@router.post("/stream")
async def stream_copywriting(
    body: CopywritingIn, db: DbDep, user: CurrentUser
) -> StreamingResponse:
    await billing.ensure_can_afford_ai(db, user, cost=COST_COPYWRITING)

    async def event_gen() -> AsyncIterator[str]:
        try:
            async for event in copywriting_service.stream_copywriting(
                db,
                user,
                prompt=body.prompt,
                asset_id=body.asset_id,
            ):
                if event.get("done"):
                    # 流式结束后重新取用户，避免长连接导致会话对象过期
                    fresh = await db.get(User, user.id)
                    if fresh is not None:
                        await billing.settle_ai_operation(
                            db,
                            fresh,
                            cost=COST_COPYWRITING,
                            kind="consume_copywriting",
                            remark="文案生成",
                        )
                    yield copywriting_service.sse_line({"done": True, "charged": COST_COPYWRITING})
                    yield "data: [DONE]\n\n"
                    return
                yield copywriting_service.sse_line(event)
        except Exception as exc:  # noqa: BLE001
            yield copywriting_service.sse_line(
                {"error": str(exc) or "文案生成失败", "done": True}
            )
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
