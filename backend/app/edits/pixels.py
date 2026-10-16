"""像素级修图算法：调色、翻转、mock 去背。"""

import io

from PIL import Image, ImageEnhance, ImageOps


def _open_rgba(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    image.load()
    return image.convert("RGBA")


def _to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def adjust_image(
    data: bytes,
    *,
    brightness: float = 0.0,
    contrast: float = 0.0,
    saturation: float = 0.0,
) -> bytes:
    """
    调色。参数取值约 -1～1：
    0 表示不变；正值增强，负值减弱。
    """
    image = _open_rgba(data)
    rgb = image.convert("RGB")

    # 映射到 Pillow Enhance：1.0 为原图，例如 +0.2 → 1.2
    if brightness:
        rgb = ImageEnhance.Brightness(rgb).enhance(1.0 + brightness)
    if contrast:
        rgb = ImageEnhance.Contrast(rgb).enhance(1.0 + contrast)
    if saturation:
        rgb = ImageEnhance.Color(rgb).enhance(1.0 + saturation)

    alpha = image.getchannel("A")
    merged = rgb.convert("RGBA")
    merged.putalpha(alpha)
    return _to_png_bytes(merged)


def flip_horizontal(data: bytes) -> bytes:
    """水平翻转。"""
    image = _open_rgba(data)
    return _to_png_bytes(ImageOps.mirror(image))


def mock_remove_background(data: bytes, threshold: int = 40) -> bytes:
    """
    mock 去背：以四角平均色为背景色，颜色接近的像素变透明。
    不依赖 rembg，保证演示环境可跑。
    """
    image = _open_rgba(data)
    pixels = image.load()
    width, height = image.size
    if width < 2 or height < 2 or pixels is None:
        return _to_png_bytes(image)

    corners = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
    ]
    avg = tuple(sum(channel[i] for channel in corners) // 4 for i in range(3))

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            distance = abs(r - avg[0]) + abs(g - avg[1]) + abs(b - avg[2])
            if distance <= threshold * 3:
                pixels[x, y] = (r, g, b, 0)

    return _to_png_bytes(image)
