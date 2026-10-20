"""裁剪 / 超分 / 扩图等几何类本地算法（mock 友好）。"""

import io

from PIL import Image


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _as_normalized_rect(
    rect: dict[str, float], width: int, height: int
) -> dict[str, float]:
    """
    统一成 0～1 归一化框。
    Agent 常误传像素坐标（如 x=134, width=200）；任一分量 >1 时按像素换算。
    """
    x = float(rect.get("x", 0))
    y = float(rect.get("y", 0))
    w = float(rect.get("width", 0))
    h = float(rect.get("height", 0))
    looks_like_pixels = max(abs(x), abs(y), abs(w), abs(h)) > 1.0 + 1e-6
    if looks_like_pixels:
        if width <= 0 or height <= 0:
            raise ValueError("图片尺寸无效，无法换算裁剪框")
        x, y, w, h = x / width, y / height, w / width, h / height

    # 钳制到画布内，避免越界放大
    x = min(max(x, 0.0), 0.999)
    y = min(max(y, 0.0), 0.999)
    w = min(max(w, 0.001), 1.0 - x)
    h = min(max(h, 0.001), 1.0 - y)
    return {"x": x, "y": y, "width": w, "height": h}


def _center_rect_for_ratio(
    width: int, height: int, ratio_w: int, ratio_h: int
) -> dict[str, float]:
    """按目标比例取画布内最大居中框（归一化）。"""
    target = ratio_w / ratio_h
    current = width / height if height else 1.0
    if current >= target:
        # 更宽：以高为边，左右裁
        norm_h = 1.0
        norm_w = target * height / width
        return {"x": (1.0 - norm_w) / 2, "y": 0.0, "width": norm_w, "height": norm_h}
    norm_w = 1.0
    norm_h = (width / target) / height
    return {"x": 0.0, "y": (1.0 - norm_h) / 2, "width": norm_w, "height": norm_h}


def crop_normalized(data: bytes, rect: dict[str, float]) -> bytes:
    """按 rect 裁剪；自动兼容归一化坐标与像素坐标。"""
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height = image.size
        box = _as_normalized_rect(rect, width, height)
        left = int(box["x"] * width)
        top = int(box["y"] * height)
        right = int((box["x"] + box["width"]) * width)
        bottom = int((box["y"] + box["height"]) * height)
        left = max(0, min(left, width - 1))
        top = max(0, min(top, height - 1))
        right = max(left + 1, min(right, width))
        bottom = max(top + 1, min(bottom, height))
        cropped = image.crop((left, top, right, bottom))
        return _png(cropped.convert("RGBA"))


def crop_by_ratio(data: bytes, ratio_w: int, ratio_h: int) -> bytes:
    """按比例居中裁剪（如 1:1 取中心正方形）。"""
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height = image.size
        box = _center_rect_for_ratio(width, height, ratio_w, ratio_h)
    return crop_normalized(data, box)


def upscale(data: bytes, scale: int = 2) -> bytes:
    """本地 Lanczos 放大。"""
    factor = max(1, min(int(scale), 4))
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height = image.size
        out = image.resize((width * factor, height * factor), Image.Resampling.LANCZOS)
        return _png(out.convert("RGBA"))


def expand_canvas(data: bytes, *, ratio_w: int, ratio_h: int) -> bytes:
    """按目标比例扩画布，原图居中，边缘用边缘色近似填充。"""
    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGBA")
        width, height = image.size
        target_ratio = ratio_w / ratio_h
        current = width / height
        if abs(current - target_ratio) < 1e-3:
            return _png(image)
        if current > target_ratio:
            new_h = int(width / target_ratio)
            new_w = width
        else:
            new_w = int(height * target_ratio)
            new_h = height
        # 取四角平均色做底板
        samples = [
            image.getpixel((0, 0)),
            image.getpixel((width - 1, 0)),
            image.getpixel((0, height - 1)),
            image.getpixel((width - 1, height - 1)),
        ]
        fill = tuple(sum(c[i] for c in samples) // 4 for i in range(4))
        canvas = Image.new("RGBA", (new_w, new_h), fill)
        ox = (new_w - width) // 2
        oy = (new_h - height) // 2
        canvas.paste(image, (ox, oy), image)
        return _png(canvas)


def replace_background_mock(data: bytes, prompt: str = "") -> bytes:
    """mock 换背景：去近似底色，铺渐变底板。"""
    del prompt
    with Image.open(io.BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        bg = Image.new("RGBA", (width, height))
        for y in range(height):
            t = y / max(height - 1, 1)
            color = (
                int(240 - 40 * t),
                int(245 - 30 * t),
                int(250 - 20 * t),
                255,
            )
            for x in range(width):
                bg.putpixel((x, y), color)
        # 简易：亮度接近四角的像素视为背景透明
        corners = [
            rgba.getpixel((0, 0))[:3],
            rgba.getpixel((width - 1, 0))[:3],
            rgba.getpixel((0, height - 1))[:3],
            rgba.getpixel((width - 1, height - 1))[:3],
        ]
        avg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
        pixels = rgba.load()
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if abs(r - avg[0]) + abs(g - avg[1]) + abs(b - avg[2]) < 45:
                    pixels[x, y] = (r, g, b, 0)
        out = Image.alpha_composite(bg, rgba)
        return _png(out)
