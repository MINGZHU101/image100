"""工作台 AI 客服：SSE 流式问答。"""

from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.deps import CurrentUser
from app.rag.retrieve import answer_question
from app.services.copywriting import sse_line

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class AssistantChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list)


@router.post("/chat/stream")
async def chat_stream(body: AssistantChatIn, user: CurrentUser) -> StreamingResponse:
    _ = user  # 需登录；本版不扣分

    async def event_gen() -> AsyncIterator[str]:
        yield sse_line({"stage": "answer", "title": "正在检索工作台教程…", "content": ""})
        try:
            history = [item.model_dump() for item in body.history]
            async for chunk in answer_question(body.message, history=history):
                yield sse_line({"stage": "answer", "content": chunk})
            yield sse_line({"done": True})
            yield "data: [DONE]\n\n"
        except Exception as exc:  # noqa: BLE001
            yield sse_line({"error": str(exc) or "客服暂时不可用", "done": True})
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
