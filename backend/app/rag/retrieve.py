"""检索教程片段并生成仅限工作台范围的回答。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.rag.index import ensure_index, get_vector_store, guide_path


_REFUSAL = (
    "抱歉，我只能回答「电商商品视觉工作台」的使用问题"
    "（例如入口在哪、怎么生成图片、文案怎么计费、如何升级会员等）。"
    "其它话题我无法协助。"
)

_SYSTEM = """你是电商商品视觉工作台的官方客服助手。
只能依据下方「知识库摘录」回答与本工作台相关的问题。
若摘录不足以回答，或问题与工作台无关（闲聊、股市、写代码、竞品等），请只回复拒答固定句，不要编造功能。
拒答固定句：""" + _REFUSAL


async def answer_question(
    question: str,
    *,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    """流式产出回答文本片段。"""
    ensure_index()
    contexts = _retrieve_texts(question, k=4)
    if not contexts or not _looks_in_domain(question, contexts):
        for chunk in _chunk(_REFUSAL, 20):
            yield chunk
        return

    context_block = "\n\n---\n\n".join(contexts)
    settings = get_settings()
    history = history or []
    history_text = ""
    for turn in history[-6:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        history_text += f"{role}: {content}\n"

    user_prompt = (
        f"知识库摘录：\n{context_block}\n\n"
        f"最近对话：\n{history_text or '（无）'}\n"
        f"用户问题：{question.strip()}\n"
        "请用简洁中文回答。"
    )

    if not settings.dashscope_api_key:
        # 无 Key：直接返回最相关片段摘要 + 提示
        summary = contexts[0][:500]
        text = f"根据教程：\n{summary}"
        for chunk in _chunk(text, 24):
            yield chunk
        return

    model = ChatOpenAI(
        model=settings.planner_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=0.2,
        streaming=True,
    )
    async for message in model.astream(
        [SystemMessage(content=_SYSTEM), HumanMessage(content=user_prompt)]
    ):
        content = getattr(message, "content", "")
        if isinstance(content, str) and content:
            yield content


def _retrieve_texts(question: str, k: int) -> list[str]:
    settings = get_settings()
    marker = settings.rag_root / ".built"
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == "fallback":
        return _fallback_retrieve(question, k)
    if not settings.dashscope_api_key:
        return _fallback_retrieve(question, k)
    try:
        store = get_vector_store()
        docs = store.similarity_search(question, k=k)
        return [doc.page_content for doc in docs if doc.page_content.strip()]
    except Exception:
        return _fallback_retrieve(question, k)


def _fallback_retrieve(question: str, k: int) -> list[str]:
    settings = get_settings()
    fallback = settings.rag_root / "fallback_chunks.txt"
    if fallback.exists():
        chunks = [c.strip() for c in fallback.read_text(encoding="utf-8").split("-----") if c.strip()]
    else:
        path = guide_path()
        if not path.exists():
            return []
        chunks = _split_plain(path.read_text(encoding="utf-8"))

    tokens = [t for t in _tokens(question) if len(t) >= 2]
    if not tokens:
        return chunks[:k]
    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        score = sum(1 for t in tokens if t in chunk)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [c for _, c in scored[:k]] or chunks[:1]


def _looks_in_domain(question: str, contexts: list[str]) -> bool:
    """简单域判断：问题含工作台关键词，或检索命中较多。"""
    keys = (
        "工作台",
        "创作",
        "编辑",
        "文案",
        "积分",
        "会员",
        "钻石",
        "生成",
        "图片",
        "登录",
        "签到",
        "充值",
        "邀请",
        "礼包",
        "客服",
        "批量",
        "导出",
        "管理员",
        "配额",
        "扣分",
        "计费",
        "image100",
        "视觉",
    )
    q = question.strip()
    if any(k in q for k in keys):
        return True
    # 无关键词时要求检索片段也含关键词，否则拒答
    joined = "\n".join(contexts)
    hit = sum(1 for k in keys if k in joined)
    return hit >= 2 and len(q) <= 80


def _split_plain(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for line in text.splitlines():
        buf.append(line)
        size += len(line)
        if size >= 500:
            parts.append("\n".join(buf).strip())
            buf, size = [], 0
    if buf:
        parts.append("\n".join(buf).strip())
    return [p for p in parts if p]


def _tokens(text: str) -> list[str]:
    import re

    return re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", text)


def _chunk(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]
