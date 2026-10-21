"""文生图多张时：对提示词改写/扩写，得到 N 条可区分变体。"""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings


async def build_prompt_variants(prompt: str, count: int) -> list[str]:
    """返回长度为 count 的提示词列表；失败时回落为带轻微扰动的原句。"""
    cleaned = prompt.strip()
    if count <= 1:
        return [cleaned]
    try:
        variants = await _llm_variants(cleaned, count)
        if len(variants) >= count:
            return variants[:count]
    except Exception:
        pass
    return _fallback_variants(cleaned, count)


async def _llm_variants(prompt: str, count: int) -> list[str]:
    settings = get_settings()
    if not settings.dashscope_api_key:
        return _fallback_variants(prompt, count)

    model = ChatOpenAI(
        model=settings.planner_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=0.85,
    )
    system = (
        "你是电商商品视觉提示词改写助手。"
        "在保留商品主体与核心卖点的前提下，改写并扩写提示词，"
        "让每条在构图角度、场景、光线、背景、镜头或风格侧重点上明显不同。"
        f"必须输出恰好 {count} 条中文提示词，且仅输出 JSON 字符串数组，不要其它说明。"
    )
    user = f"原提示词：{prompt}\n请生成 {count} 条变体。"
    message = await model.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    text = _message_text(message)
    parsed = _parse_json_array(text)
    cleaned = [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
    if len(cleaned) < count:
        raise ValueError("变体数量不足")
    return cleaned


def _fallback_variants(prompt: str, count: int) -> list[str]:
    """无 Key 或 LLM 失败时的本地扰动，保证 Mock 也能区分。"""
    suffixes = [
        "，正面平视，柔和棚拍光，浅色背景",
        "，三分法构图，侧光强调质感，生活场景",
        "，俯拍 45 度，暖色氛围光，简约背景",
        "，特写镜头突出材质细节，高对比光影",
        "，广角展示整体陈列，自然窗光",
        "，低角度仰拍增强高级感，冷色调背景",
    ]
    result: list[str] = []
    for index in range(count):
        result.append(f"{prompt}{suffixes[index % len(suffixes)]}")
    return result


def _message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        ).strip()
    return str(content or "").strip()


def _parse_json_array(text: str) -> list:
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        raise ValueError("未找到 JSON 数组")
    data = json.loads(match.group(0))
    if not isinstance(data, list):
        raise ValueError("JSON 不是数组")
    return data
