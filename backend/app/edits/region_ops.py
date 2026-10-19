"""局部消除 / 替换 / 提升为图层（本地 mock）。"""

import hashlib
import io

from PIL import Image

from app.edits.mask import apply_masked, mask_from_selection


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def erase_region(data: bytes, selection: dict) -> bytes:
    """选区内填充为邻近平均色（简易消除）。"""
    with Image.open(io.BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        mask = mask_from_selection((width, height), selection)
        # 用整图平均色填充（演示级）
        pixels = list(rgba.getdata())
        count = max(len(pixels), 1)
        avg = tuple(sum(p[i] for p in pixels) // count for i in range(4))
        fill = Image.new("RGBA", (width, height), avg)
        return apply_masked(data, _png(fill), mask)


def replace_region(data: bytes, selection: dict, prompt: str = "") -> bytes:
    """选区内铺色块（由 prompt 哈希决定颜色），mock 局部替换。"""
    digest = hashlib.md5((prompt or "mock").encode("utf-8")).digest()
    color = (digest[0], digest[1], digest[2], 255)
    with Image.open(io.BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        mask = mask_from_selection((width, height), selection)
        fill = Image.new("RGBA", (width, height), color)
        return apply_masked(data, _png(fill), mask)


def cutout_region(data: bytes, selection: dict) -> bytes:
    """按选区抠出透明底的主体图，供 promote 成层。"""
    with Image.open(io.BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        mask = mask_from_selection((width, height), selection)
        out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        out.paste(rgba, (0, 0), mask)
        return _png(out)
