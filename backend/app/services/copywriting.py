"""电商商品文案生成：分阶段流式（看图/卖点 → 标题 → 正文+标签）。"""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User
from app.services import assets as assets_service
from app.storage import get_storage


async def stream_copywriting(
    session: AsyncSession,
    user: User,
    *,
    prompt: str,
    asset_id: UUID | None = None,
) -> AsyncIterator[dict]:
    """产出 SSE 事件 dict：stage / title / content / done。"""
    image_note = ""
    if asset_id is not None:
        yield {"stage": "1/3", "title": "正在看图，提炼卖点…", "content": ""}
        try:
            image_note = await _describe_product_image(session, user, asset_id)
            if not image_note:
                image_note = "（未识别到有效画面描述，将主要依据文字提示）"
        except Exception as exc:  # noqa: BLE001
            # 模型名未开通 / 视觉接口失败时不中断整次生成，降级为纯文字
            image_note = _friendly_vision_error(exc)
        for chunk in _chunk_text(image_note, 24):
            yield {"stage": "1/3", "title": "正在看图，提炼卖点…", "content": chunk}
    else:
        yield {"stage": "1/3", "title": "正在分析卖点…", "content": ""}
        # _stream_stage 是 async generator，只能 async for，不能 await
        async for chunk in _stream_stage(
            system=(
                "你是电商金牌文案策划。根据用户描述，用简短中文列出："
                "目标人群、核心痛点、3 个卖点转化。不要写标题和正文。"
            ),
            user_text=f"产品描述：{prompt.strip()}",
            vision_model=False,
        ):
            yield {"stage": "1/3", "title": "正在分析卖点…", "content": chunk}
            image_note += chunk

    brief = f"用户提示：{prompt.strip()}\n卖点/看图笔记：\n{image_note.strip()}"

    yield {"stage": "2/3", "title": "正在撰写标题…", "content": ""}
    title_buf = ""
    async for chunk in _stream_stage(
        system=(
            "你是电商标题专家。根据资料写 1～2 条吸睛中文主标题，"
            "可含适量情绪词，不要正文、不要标签、不要解释。"
        ),
        user_text=brief,
        vision_model=False,
    ):
        title_buf += chunk
        yield {"stage": "2/3", "title": "正在撰写标题…", "content": chunk}

    yield {"stage": "3/3", "title": "正在撰写正文与标签…", "content": ""}
    async for chunk in _stream_stage(
        system=(
            "你是电商金牌文案专家。输出 Markdown："
            "## 正文\n（一段有转化力的商品描述）\n\n## 标签\n（3～6 个 #标签）\n"
            "不要重复写标题；风格口语、有网感。"
        ),
        user_text=f"{brief}\n已定标题：\n{title_buf.strip()}",
        vision_model=False,
    ):
        yield {"stage": "3/3", "title": "正在撰写正文与标签…", "content": chunk}

    yield {"done": True}


async def _describe_product_image(
    session: AsyncSession, user: User, asset_id: UUID
) -> str:
    asset = await assets_service.get_asset_or_404(session, asset_id, user)
    data = get_storage().get(asset.storage_key)
    mime = asset.mime or "image/png"
    b64 = base64.b64encode(data).decode("ascii")
    settings = get_settings()
    if not settings.dashscope_api_key:
        return "（演示模式：未配置视觉 Key，跳过看图）"

    model = ChatOpenAI(
        model=settings.vision_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=0.3,
    )
    message = await model.ainvoke(
        [
            SystemMessage(
                content="你是电商视觉分析师。用中文简要描述商品外观、材质、使用场景与可写文案的卖点。"
            ),
            HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {"type": "text", "text": "请分析这张商品图。"},
                ]
            ),
        ]
    )
    return _message_text(message)


async def _stream_stage(
    *,
    system: str,
    user_text: str,
    vision_model: bool,
) -> AsyncIterator[str]:
    settings = get_settings()
    if not settings.dashscope_api_key:
        text = _mock_stage_text(system, user_text)
        for chunk in _chunk_text(text, 18):
            yield chunk
        return

    model_name = settings.vision_model if vision_model else settings.planner_model
    model = ChatOpenAI(
        model=model_name,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=0.7,
        streaming=True,
    )
    async for message in model.astream(
        [SystemMessage(content=system), HumanMessage(content=user_text)]
    ):
        piece = _message_text(message)
        if piece:
            yield piece


def _mock_stage_text(system: str, user_text: str) -> str:
    if "标题" in system:
        return "清晨的第一杯好心情，从这件好物开始"
    if "正文" in system or "标签" in system:
        return (
            "## 正文\n把日常用得到的质感与便利写进细节，让下单理由更充分。"
            "\n\n## 标签\n#好物推荐 #电商必备 #品质生活"
        )
    return f"目标人群：追求品质的买家\n痛点：选择困难\n卖点：好用、好看、好入手\n（基于：{user_text[:80]}）"


def _chunk_text(text: str, size: int) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def _message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return str(content or "")


def _friendly_vision_error(exc: Exception) -> str:
    text = str(exc)
    if "model_not_found" in text or "Model not exist" in text:
        return (
            "（看图模型未开通或名称不可用，已改为仅根据文字提示写文案。"
            "可在 .env 设置 VISION_MODEL=qwen-vl-max 或 qwen2.5-vl-72b-instruct 后重试）"
        )
    return f"（看图暂时失败：{text[:120]}。将主要依据文字提示继续生成）"


def sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
