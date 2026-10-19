"""裁剪 / 超分 / 扩图等几何类本地算法（mock 友好）。"""

import io

from PIL import Image


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def crop_normalized(data: bytes, rect: dict[str, float]) -> bytes:
    """按归一化 rect 裁剪。"""
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height = image.size
        left = int(rect["x"] * width)
        top = int(rect["y"] * height)
        right = int((rect["x"] + rect["width"]) * width)
        bottom = int((rect["y"] + rect["height"]) * height)
        right = max(right, left + 1)
        bottom = max(bottom, top + 1)
        cropped = image.crop((left, top, right, bottom))
        return _png(cropped.convert("RGBA"))


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
