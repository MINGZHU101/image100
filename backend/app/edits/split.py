"""主体/背景拆分：mock 去背 + 本地填洞。"""

import io

from PIL import Image, ImageChops, ImageFilter

from app.edits import pixels


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def alpha_mask_luma(subject_png: bytes) -> Image.Image:
    """从主体 PNG 透明通道得到 L 掩膜。"""
    alpha = Image.open(io.BytesIO(subject_png)).convert("RGBA").getchannel("A")
    return alpha


def fill_background(source: bytes, mask: Image.Image) -> bytes:
    """
    挖掉掩膜覆盖像素并用周围色填洞。
    优先尝试 OpenCV inpaint；失败则用 Pillow blur 兜底。
    """
    image = Image.open(io.BytesIO(source)).convert("RGB")
    luma = mask.convert("L")
    if luma.size != image.size:
        luma = luma.resize(image.size, Image.Resampling.NEAREST)

    try:
        filled = _cv_inpaint(image, luma)
    except Exception:
        filled = _blur_inpaint(image, luma)
    return _png(filled.convert("RGBA"))


def split_to_subject_background(source: bytes) -> tuple[bytes, bytes]:
    """
    拆成主体（透明底）与背景（主体位置已填洞）。
    返回 (subject_png, background_png)。
    """
    subject = pixels.mock_remove_background(source)
    mask = alpha_mask_luma(subject)
    # 略外扩，减少主体边缘残留在背景上
    expanded = mask.filter(ImageFilter.MaxFilter(9))
    background = fill_background(source, expanded)
    return subject, background


def composite_layers(layer_images: list[bytes], size: tuple[int, int]) -> bytes:
    """自下而上 alpha 合成多层，用于导出。"""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    for data in layer_images:
        layer = Image.open(io.BytesIO(data)).convert("RGBA")
        if layer.size != size:
            layer = layer.resize(size, Image.Resampling.LANCZOS)
        canvas = Image.alpha_composite(canvas, layer)
    return _png(canvas)


def _cv_inpaint(image: Image.Image, luma: Image.Image) -> Image.Image:
    import cv2
    import numpy as np

    hole = np.where(np.array(luma) > 12, 255, 0).astype("uint8")
    if not hole.any():
        return image
    radius = max(3, min(image.size) // 80)
    repaired = cv2.inpaint(np.array(image), hole, radius, cv2.INPAINT_TELEA)
    return Image.fromarray(repaired)


def _blur_inpaint(image: Image.Image, luma: Image.Image) -> Image.Image:
    """未安装 OpenCV 时的兜底：边界平均色铺底 + 模糊抹平。"""
    keep = ImageChops.invert(luma)
    ring = ImageChops.subtract(luma.filter(ImageFilter.MaxFilter(9)), luma)
    seed_color = _mean_where(image, ring) or _mean_where(image, keep) or (200, 200, 200)
    seed = Image.new("RGB", image.size, seed_color)
    seed.paste(image, mask=keep)
    patched = seed
    for radius in (24, 12, 5):
        patched = Image.composite(
            patched.filter(ImageFilter.GaussianBlur(radius)),
            patched,
            luma,
        )
    return Image.composite(patched, image, luma)


def _mean_where(
    image: Image.Image, mask: Image.Image
) -> tuple[int, int, int] | None:
    pixels_map = image.load()
    levels = mask.load()
    total = [0, 0, 0]
    count = 0
    for y in range(image.height):
        for x in range(image.width):
            if levels[x, y] <= 16:
                continue
            red, green, blue = pixels_map[x, y][:3]
            total[0] += red
            total[1] += green
            total[2] += blue
            count += 1
    if not count:
        return None
    return (total[0] // count, total[1] // count, total[2] // count)
