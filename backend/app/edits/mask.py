"""选区掩膜：矩形/笔画栅格化，以及选区内合成。"""

import io

from PIL import Image, ImageChops, ImageDraw, ImageFilter


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _dot(draw: ImageDraw.ImageDraw, point: tuple[float, float], brush: int) -> None:
    x, y = point
    radius = brush / 2
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)


def rasterize_rect(
    size: tuple[int, int],
    rect: dict[str, float],
) -> Image.Image:
    """将归一化矩形栅格化为 L 掩膜（选中=255）。"""
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    left = int(rect["x"] * width)
    top = int(rect["y"] * height)
    right = int((rect["x"] + rect["width"]) * width)
    bottom = int((rect["y"] + rect["height"]) * height)
    # 至少 1 像素，避免浮点截断成空选区
    right = max(right, left + 1)
    bottom = max(bottom, top + 1)
    draw.rectangle((left, top, right, bottom), fill=255)
    return mask


def rasterize_strokes(
    size: tuple[int, int],
    strokes: list[list[list[float]]],
    *,
    radius: float,
) -> Image.Image:
    """
    笔画栅格化：多点闭合填涂 + 线宽兜底。
    radius 为相对短边比例（默认约 0.03）。
    """
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    brush = max(2, int(min(width, height) * radius))
    for stroke in strokes:
        if not stroke:
            continue
        points = [(float(x) * width, float(y) * height) for x, y in stroke]
        if len(points) == 1:
            _dot(draw, points[0], brush)
            continue
        if len(points) > 2:
            draw.polygon(points, fill=255)
        draw.line(points, fill=255, width=brush, joint="curve")
        for point in points:
            _dot(draw, point, brush)
    return mask


def mask_from_selection(
    size: tuple[int, int],
    selection: dict,
) -> Image.Image:
    """根据 document.selection 生成 L 掩膜。"""
    sel_type = selection.get("type")
    if sel_type == "rect":
        rect = selection.get("rect") or {}
        return rasterize_rect(size, rect)
    if sel_type == "brush":
        strokes = selection.get("strokes") or []
        radius = float(selection.get("brush_radius") or 0.03)
        return rasterize_strokes(size, strokes, radius=radius)
    raise ValueError(f"不支持的选区类型：{sel_type}")


def apply_masked(source: bytes, edited: bytes, mask: Image.Image) -> bytes:
    """只把选区内的像素换成编辑结果，选区外保持原图。"""
    original = Image.open(io.BytesIO(source)).convert("RGBA")
    result = Image.open(io.BytesIO(edited)).convert("RGBA")
    if result.size != original.size:
        result = result.resize(original.size, Image.Resampling.LANCZOS)
    luma = mask.convert("L")
    if luma.size != original.size:
        luma = luma.resize(original.size, Image.Resampling.NEAREST)
    # 轻微羽化，避免硬边（无产品开关）
    luma = luma.filter(ImageFilter.GaussianBlur(1.2))
    return _png(Image.composite(result, original, luma))


def union(left: Image.Image, right: Image.Image) -> Image.Image:
    return ImageChops.lighter(left.convert("L"), right.convert("L"))
