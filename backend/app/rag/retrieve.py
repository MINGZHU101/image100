"""检索教程片段并生成工作台范围内的客服回答。"""

from __future__ import annotations

from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.rag.index import ensure_index, get_vector_store, guide_path


_REFUSAL = (
    "抱歉，我主要解答「电商商品视觉工作台」的使用问题"
    "（例如：生成图片在哪、怎么充值换积分、文案怎么计费、如何升级会员、批量怎么下载等）。"
    "若你的问题与本站无关，我暂时无法协助；换个本站使用问题再问我吧。"
)

_SYSTEM = """你是「电商商品视觉工作台」的官方智能客服。

回答原则：
1. 优先依据下方「知识库摘录」作答，用简洁中文，步骤清楚，可指出侧栏入口名称（创作/文案/编辑/导出/批量/个人中心）。
2. 用户问题只要与本工作台使用相关（找图、生图、充值、积分、会员、批量、导出、登录、转盘、计费、报错提示等），即使措辞口语化也要尽力回答。
3. 摘录未直接写到、但能由摘录合理推断的操作路径，可以简要说明，并注明「以页面实际按钮为准」。
4. 不要编造不存在的菜单、价格或第三方竞品功能。
5. 仅当问题明显与本站无关（闲聊八卦、股市荐股、写无关代码作业、政治等）时，才回复拒答固定句。
拒答固定句：""" + _REFUSAL

# 工作台相关信号词：命中则视为站内问题，交给检索 + LLM
_DOMAIN_KEYS = (
    "工作台",
    "创作",
    "编辑",
    "文案",
    "积分",
    "会员",
    "钻石",
    "青铜",
    "白银",
    "黄金",
    "铂金",
    "生成",
    "图片",
    "生图",
    "登录",
    "注册",
    "签到",
    "充值",
    "兑换",
    "余额",
    "钱包",
    "邀请",
    "礼包",
    "客服",
    "批量",
    "导出",
    "管理员",
    "配额",
    "扣分",
    "计费",
    "收费",
    "花费",
    "多少分",
    "image100",
    "视觉",
    "素材",
    "候选",
    "历史",
    "上传",
    "下载",
    "打包",
    "进度",
    "转盘",
    "抽奖",
    "Agent",
    "agent",
    "去背",
    "换背景",
    "超分",
    "扩图",
    "调色",
    "密码",
    "头像",
    "账号",
    "公告",
    "入口",
    "在哪",
    "哪里",
    "怎么",
    "如何",
    "怎样",
    "什么",
    "为何",
    "为什么",
    "失败",
    "报错",
    "401",
    "key",
    "Key",
    "演示",
    "demo",
)


async def answer_question(
    question: str,
    *,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    """流式产出回答文本片段。"""
    ensure_index()
    q = question.strip()
    contexts = _retrieve_texts(q, k=6)
    off_topic = _is_clearly_off_topic(q)

    if off_topic:
        for chunk in _chunk(_REFUSAL, 20):
            yield chunk
        return

    if not contexts:
        # 站内问题但检索空：给引导，避免误伤「充值/找图」等口语问法
        guide = (
            "我暂时没检索到足够片段，你可以换个问法，例如：\n"
            "· 生成图片在哪里？\n"
            "· 怎么充值兑换积分？\n"
            "· 文案生成扣多少分？\n"
            "· 批量结果如何打包下载？\n"
            "· 怎么升级到钻石会员？"
        )
        for chunk in _chunk(guide, 24):
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
        f"用户问题：{q}\n"
        "请直接回答用户问题；需要步骤时分点列出。"
    )

    if not settings.dashscope_api_key:
        # 无 Key：用检索片段拼一份可读回答
        text = _fallback_answer(q, contexts)
        for chunk in _chunk(text, 24):
            yield chunk
        return

    model = ChatOpenAI(
        model=settings.planner_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=0.3,
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
        texts = [doc.page_content for doc in docs if doc.page_content.strip()]
        # 向量结果偏少时，用关键词检索补足
        if len(texts) < max(2, k // 2):
            extra = _fallback_retrieve(question, k)
            for chunk in extra:
                if chunk not in texts:
                    texts.append(chunk)
                if len(texts) >= k:
                    break
        return texts
    except Exception:
        return _fallback_retrieve(question, k)


def _fallback_retrieve(question: str, k: int) -> list[str]:
    settings = get_settings()
    fallback = settings.rag_root / "fallback_chunks.txt"
    if fallback.exists():
        chunks = [
            c.strip()
            for c in fallback.read_text(encoding="utf-8").split("-----")
            if c.strip()
        ]
    else:
        path = guide_path()
        if not path.exists():
            return []
        chunks = _split_plain(path.read_text(encoding="utf-8"))

    tokens = [t for t in _tokens(question) if len(t) >= 2]
    # 同义扩展，提升「充值/找图」等口语命中
    expanded = set(tokens)
    synonym_map = {
        "充值": ["充值", "兑换", "余额", "积分", "钱包"],
        "充钱": ["充值", "兑换", "余额"],
        "买分": ["充值", "兑换", "积分"],
        "图片": ["图片", "创作", "生成", "素材", "候选", "历史"],
        "生图": ["生成", "创作", "图片"],
        "在哪": ["入口", "创作", "侧栏", "哪里"],
        "哪里": ["入口", "创作", "侧栏", "在哪"],
        "下载": ["打包", "批量", "导出", "下载"],
        "会员": ["会员", "钻石", "等级", "升级"],
        "升级": ["会员", "钻石", "消耗", "升级"],
    }
    for token in list(tokens):
        for key, extras in synonym_map.items():
            if key in token or token in key:
                expanded.update(extras)

    if not expanded:
        return chunks[:k]

    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        score = sum(1 for t in expanded if t in chunk)
        # FAQ 段落加权
        if "**问：" in chunk or "问：" in chunk:
            score += 1
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored:
        return [c for _, c in scored[:k]]
    # 无分时仍返回教程前几块，避免整站拒答
    return chunks[:k]


def _fallback_answer(question: str, contexts: list[str]) -> str:
    """无大模型 Key 时的可读拼接。"""
    best = contexts[0]
    tip = ""
    if any(k in question for k in ("充值", "兑换", "买分", "充钱")):
        tip = (
            "简要说明：打开「个人中心」→ 先模拟充值到余额 → 再兑换成积分"
            "（默认约 1 元 = 10 积分，以页面为准）。\n\n"
        )
    elif any(k in question for k in ("图片", "生图", "生成", "在哪", "哪里")):
        tip = (
            "简要说明：左侧进「创作」生成；结果在候选页查看，之后可在历史素材中打开；"
            "批量结果在「批量」进度页可打包下载。\n\n"
        )
    return f"{tip}根据教程：\n{best[:700]}"


def _is_clearly_off_topic(question: str) -> bool:
    """仅拦截明显站外话题；默认偏宽松，让检索 + LLM 处理站内口语。"""
    q = question.strip()
    if not q:
        return True
    if any(k in q for k in _DOMAIN_KEYS):
        return False
    # 无任何站内信号时，再看是否像闲聊/站外
    off = (
        "股票",
        "基金",
        "比特币",
        "今天天气",
        "讲个笑话",
        "帮我写诗",
        "恋爱",
        "星座",
        "政治",
        "谁是总统",
    )
    if any(k in q for k in off):
        return True
    # 极短且无领域词：仍尝试回答（由检索兜底），不直接拒答
    return False


def _split_plain(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for line in text.splitlines():
        # 按标题切开，避免一块过大
        if line.startswith("## ") and buf:
            parts.append("\n".join(buf).strip())
            buf, size = [line], len(line)
            continue
        buf.append(line)
        size += len(line)
        if size >= 550:
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
