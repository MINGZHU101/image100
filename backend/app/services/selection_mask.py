"""根据笔刷选区生成简易 PNG mask，供原仓前端 SelectionOverlay 显示。"""

from __future__ import annotations

import io
import uuid
from typing import Any
from uuid import UUID

from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import DEMO_USER_ID
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
        owner_id=UUID(DEMO_USER_ID),
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
