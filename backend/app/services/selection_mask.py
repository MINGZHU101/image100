"""根据笔刷选区生成简易 PNG mask，供原仓前端 SelectionOverlay 显示。"""

from __future__ import annotations

import io
import uuid
from typing import Any
from uuid import UUID

from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.services.assets import asset_file_url
from app.storage import get_storage


def _canvas_size(document: dict[str, Any]) -> tuple[int, int]:
    canvas = document.get("canvas") or {}
    width = int(canvas.get("width") or document.get("width") or 1024)
    height = int(canvas.get("height") or document.get("height") or 1024)
    return max(width, 1), max(height, 1)


def render_brush_mask(
    *,
    width: int,
    height: int,
    strokes: list[list[list[float]]],
    brush_radius: float,
) -> bytes:
    """归一化笔刷 → RGBA mask（选中区不透明白）。"""
    # 青色半透明，与前端草稿预览 (#5f98ad) 一致，松手后仍清晰可见
    ink = (95, 152, 173, 200)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius_px = max(1, int(min(width, height) * brush_radius))
    for stroke in strokes:
        if len(stroke) < 2:
            continue
        points = [(float(p[0]) * width, float(p[1]) * height) for p in stroke if len(p) >= 2]
        if len(points) < 2:
            continue
        draw.line(points, fill=ink, width=radius_px * 2)
        for x, y in points:
            draw.ellipse(
                (x - radius_px, y - radius_px, x + radius_px, y + radius_px),
                fill=ink,
            )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def apply_brush_selection(
    session: AsyncSession,
    row: EditSession,
    *,
    strokes: list[list[dict[str, float]]] | list[list[list[float]]],
    radius: float,
    append: bool,
) -> dict[str, Any]:
    """写入 document.selection（本仓 brush）并生成 mask 资产。"""
    document = dict(row.document or {})
    width, height = _canvas_size(document)

    # 统一成 [[x,y], ...]
    normalized: list[list[list[float]]] = []
    for stroke in strokes:
        points: list[list[float]] = []
        for point in stroke:
            if isinstance(point, dict):
                points.append([float(point["x"]), float(point["y"])])
            else:
                points.append([float(point[0]), float(point[1])])
        if points:
            normalized.append(points)

    existing = document.get("selection") if append else None
    merged = list(normalized)
    if (
        append
        and isinstance(existing, dict)
        and existing.get("type") == "brush"
        and existing.get("strokes")
    ):
        merged = list(existing["strokes"]) + normalized

    if not merged:
        raise ValueError("strokes 不能为空")

    brush_radius = float(radius or 0.03)
    document["selection"] = {
        "type": "brush",
        "strokes": merged,
        "brush_radius": brush_radius,
        "feather": 0.0,
    }

    mask_bytes = render_brush_mask(
        width=width,
        height=height,
        strokes=merged,
        brush_radius=brush_radius,
    )
    asset_id = uuid.uuid4()
    storage_key = f"objects/{asset_id}.png"
    get_storage().put(storage_key, mask_bytes, "image/png")
    asset = Asset(
        id=asset_id,
        owner_id=row.owner_id,
        storage_key=storage_key,
        width=width,
        height=height,
        mime="image/png",
    )
    session.add(asset)
    document["selection_mask_asset_id"] = str(asset_id)
    document["selection_revision"] = int(document.get("selection_revision") or 0) + 1
    row.document = document
    flag_modified(row, "document")
    await session.commit()
    await session.refresh(row)
    await session.refresh(asset)

    revision = int(document["selection_revision"])
    return {
        "revision": revision,
        "mask": {
            "id": str(asset.id),
            "kind": "mask",
            "source": "tool",
            "image_format": "png",
            "width": asset.width,
            "height": asset.height,
            "size_bytes": len(mask_bytes),
            "has_alpha": True,
            "created_at": asset.created_at.isoformat(),
            "url": asset_file_url(asset.id),
        },
        "markers": [],
    }


def render_point_mask(
    *,
    width: int,
    height: int,
    points: list[dict[str, float]],
    image_bytes: bytes | None = None,
) -> tuple[bytes, list[dict[str, Any]]]:
    """
    简化点选：在点击处画椭圆选区（mock，非 SAM）。
    多点则并集；markers 供前端角标。
    """
    ink = (95, 152, 173, 200)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = max(8, int(min(width, height) * 0.08))
    markers: list[dict[str, Any]] = []
    del image_bytes  # 预留：后续可用颜色洪水填充
    for index, point in enumerate(points):
        x = float(point["x"]) * width
        y = float(point["y"]) * height
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=ink)
        markers.append({"index": index + 1, "x": float(point["x"]), "y": float(point["y"])})
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue(), markers


async def apply_point_selection(
    session: AsyncSession,
    row: EditSession,
    *,
    points: list[dict[str, float]],
    append: bool,
) -> dict[str, Any]:
    """点选 → document.selection(rect 近似) + mask 资产。"""
    if not points:
        raise ValueError("points 不能为空")
    document = dict(row.document or {})
    width, height = _canvas_size(document)
    mask_bytes, markers = render_point_mask(width=width, height=height, points=points)

    # 用包围盒近似写入 rect selection，供 adjust_region / erase 使用
    xs = [float(p["x"]) for p in points]
    ys = [float(p["y"]) for p in points]
    pad = 0.08
    x0 = max(0.0, min(xs) - pad)
    y0 = max(0.0, min(ys) - pad)
    x1 = min(1.0, max(xs) + pad)
    y1 = min(1.0, max(ys) + pad)
    document["selection"] = {
        "type": "rect",
        "rect": {"x": x0, "y": y0, "width": max(x1 - x0, 0.02), "height": max(y1 - y0, 0.02)},
        "feather": 0.0,
    }
    if append and markers:
        prev = document.get("selection_markers") or []
        markers = list(prev) + markers

    asset_id = uuid.uuid4()
    storage_key = f"objects/{asset_id}.png"
    get_storage().put(storage_key, mask_bytes, "image/png")
    asset = Asset(
        id=asset_id,
        owner_id=row.owner_id,
        storage_key=storage_key,
        width=width,
        height=height,
        mime="image/png",
    )
    session.add(asset)
    document["selection_mask_asset_id"] = str(asset_id)
    document["selection_markers"] = markers
    document["selection_revision"] = int(document.get("selection_revision") or 0) + 1
    row.document = document
    flag_modified(row, "document")
    await session.commit()
    await session.refresh(row)
    await session.refresh(asset)
    return {
        "revision": int(document["selection_revision"]),
        "mask": {
            "id": str(asset.id),
            "kind": "mask",
            "source": "tool",
            "image_format": "png",
            "width": asset.width,
            "height": asset.height,
            "size_bytes": len(mask_bytes),
            "has_alpha": True,
            "created_at": asset.created_at.isoformat(),
            "url": asset_file_url(asset.id),
        },
        "markers": markers,
    }


def selection_payload_from_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    """从 document 还原前端 Selection；无 mask 则 None。"""
    doc = document or {}
    mask_id = doc.get("selection_mask_asset_id")
    if not mask_id or not doc.get("selection"):
        return None
    return {
        "revision": int(doc.get("selection_revision") or 0),
        "mask_asset_id": str(mask_id),
        "selection": doc.get("selection"),
    }
