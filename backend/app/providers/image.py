"""文生图 Provider：mock 占位图与 DashScope 兼容端点。"""

import hashlib
import io
from typing import Protocol

import colorsys
import httpx
from PIL import Image, ImageDraw

from app.config import get_settings


class ImageProviderError(Exception):
    """生图失败。"""


class ImageProvider(Protocol):
    name: str

    async def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        count: int,
    ) -> list[bytes]:
        """返回 count 张 PNG 字节。"""
        ...


def get_image_provider(name: str | None = None) -> ImageProvider:
    settings = get_settings()
    chosen = (name or settings.image_provider or "dashscope").strip().lower()
    if chosen == "mock":
        return MockImageProvider()
    if chosen == "dashscope":
        return DashscopeImageProvider()
    raise ValueError(f"未知生图 Provider：{chosen}")


class MockImageProvider:
    """按 prompt 哈希生成稳定占位图，便于无 Key 演示。"""

    name = "mock"

    async def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        count: int,
    ) -> list[bytes]:
        seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
        return [
            _render_placeholder(prompt, width, height, seed + index * 977, index)
            for index in range(count)
        ]


class DashscopeImageProvider:
    """OpenAI 兼容 images/generations（与规划器共用 compatible-mode 基址）。"""

    name = "dashscope"

    async def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        count: int,
    ) -> list[bytes]:
        settings = get_settings()
        if not settings.dashscope_api_key:
            raise ImageProviderError("未配置 DASHSCOPE_API_KEY，请切换到 Mock")

        # 原生协议：size 用星号，n 为张数
        payload = {
            "model": settings.text_to_image_model,
            "input": {
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]},
                ]
            },
            "parameters": {
                "size": f"{width}*{height}",
                "n": count,
                "watermark": False,
            },
        }
        headers = {
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                settings.dashscope_image_url,
                json=payload,
                headers=headers,
            )
            if response.status_code >= 400:
                raise ImageProviderError(
                    f"DashScope 生图失败 HTTP {response.status_code}: {response.text[:400]}"
                )
            body = response.json()
            urls = _extract_image_urls(body)
            if not urls:
                raise ImageProviderError(f"DashScope 未返回图片：{str(body)[:400]}")
            images: list[bytes] = []
            for image_url in urls:
                downloaded = await client.get(image_url)
                if downloaded.status_code >= 400:
                    raise ImageProviderError(f"下载生成图失败 HTTP {downloaded.status_code}")
                images.append(downloaded.content)
        return images


def _extract_image_urls(body: dict) -> list[str]:
    """兼容 OpenAI data[].url 与 DashScope choices[].message.content[].image。"""
    urls: list[str] = []
    for item in body.get("data") or []:
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    output = body.get("output") or {}
    for choice in output.get("choices") or []:
        message = choice.get("message") or {}
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("image"):
                urls.append(block["image"])
    return urls


def _render_placeholder(
    prompt: str,
    width: int,
    height: int,
    seed: int,
    index: int,
) -> bytes:
    hue = (seed % 360) / 360
    base = tuple(int(channel * 255) for channel in colorsys.hls_to_rgb(hue, 0.82, 0.38))
    accent = tuple(
        int(channel * 255) for channel in colorsys.hls_to_rgb((hue + 0.5) % 1, 0.45, 0.5)
    )
    image = Image.new("RGB", (width, height), base)
    draw = ImageDraw.Draw(image)
    short = min(width, height)
    radius = short // 3
    cx, cy = width // 2, height // 2
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent)
    draw.text((16, 16), f"{prompt[:48]}\n#{index + 1}", fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
