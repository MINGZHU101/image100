"""将会话文档规范化为原仓前端可用的 SessionDetail 形状。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.services.assets import asset_file_url, to_asset_out


def _default_transform() -> dict[str, float]:
    return {"x": 0, "y": 0, "scale_x": 1, "scale_y": 1, "rotation": 0}


def normalize_layer(layer: dict[str, Any], canvas_w: int, canvas_h: int) -> dict[str, Any]:
    """补齐原仓 Layer 字段；本仓精简层无 transform/kind 时给默认值。"""
    asset_id = layer.get("asset_id")
    return {
        "id": str(layer.get("id") or ""),
        "kind": layer.get("kind") or "image",
        "name": layer.get("name") or "图层",
        "width": int(layer.get("width") or canvas_w),
        "height": int(layer.get("height") or canvas_h),
        "asset_id": str(asset_id) if asset_id else None,
        "transform": layer.get("transform") or _default_transform(),
        "opacity": float(layer.get("opacity") if layer.get("opacity") is not None else 1),
        "visible": bool(layer.get("visible", True)),
        "locked": bool(layer.get("locked", False)),
        "source_hash": layer.get("source_hash"),
        "text": layer.get("text"),
        "font_size": layer.get("font_size"),
        "fill": layer.get("fill"),
    }


def normalize_document(document: dict[str, Any] | None) -> dict[str, Any]:
    """本仓 document（canvas + layers）→ 原仓 LayerDocument（width/height + layers）。"""
    doc = dict(document or {})
    canvas = doc.get("canvas") or {}
    width = int(canvas.get("width") or doc.get("width") or 1024)
    height = int(canvas.get("height") or doc.get("height") or 1024)
    layers = [normalize_layer(item, width, height) for item in (doc.get("layers") or [])]
    return {
        "width": width,
        "height": height,
        "layers": layers,
        # 本仓扩展字段，前端可忽略
        "active_layer_id": doc.get("active_layer_id"),
        "selection": doc.get("selection"),
        "version": doc.get("version", 1),
    }


def asset_ids_from_document(document: dict[str, Any] | None) -> list[UUID]:
    """收集文档中引用的资产 ID。"""
    ids: list[UUID] = []
    for layer in (document or {}).get("layers") or []:
        raw = layer.get("asset_id")
        if not raw:
            continue
        try:
            ids.append(UUID(str(raw)))
        except ValueError:
            continue
    mask_id = (document or {}).get("selection_mask_asset_id")
    if mask_id:
        try:
            ids.append(UUID(str(mask_id)))
        except ValueError:
            pass
    # 去重且保序
    seen: set[UUID] = set()
    ordered: list[UUID] = []
    for item in ids:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def current_asset_id(document: dict[str, Any] | None) -> str | None:
    """当前活动层资产；否则取最上层有资产的层。"""
    doc = document or {}
    layers = list(doc.get("layers") or [])
    active = doc.get("active_layer_id")
    if active:
        for layer in layers:
            if str(layer.get("id")) == str(active) and layer.get("asset_id"):
                return str(layer["asset_id"])
    for layer in reversed(layers):
        if layer.get("asset_id"):
            return str(layer["asset_id"])
    return None


def original_asset_id(document: dict[str, Any] | None) -> str | None:
    """优先主图层，否则第一层。"""
    layers = list((document or {}).get("layers") or [])
    for layer in layers:
        if str(layer.get("id")) == "layer_main" and layer.get("asset_id"):
            return str(layer["asset_id"])
    for layer in layers:
        if layer.get("asset_id"):
            return str(layer["asset_id"])
    return None


async def build_session_detail(session: AsyncSession, row: EditSession) -> dict[str, Any]:
    """组装原仓 SessionDetail 兼容字典。"""
    from app.services import history as history_service

    document = row.document or {}
    asset_ids = asset_ids_from_document(document)
    assets_out: list[dict[str, Any]] = []
    if asset_ids:
        result = await session.execute(select(Asset).where(Asset.id.in_(asset_ids)))
        assets = list(result.scalars().all())
        by_id = {item.id: item for item in assets}
        for asset_id in asset_ids:
            asset = by_id.get(asset_id)
            if asset is None:
                continue
            out = to_asset_out(asset)
            assets_out.append(
                {
                    "id": str(out.id),
                    "kind": "original",
                    "source": "upload",
                    "image_format": out.mime.split("/")[-1],
                    "width": out.width,
                    "height": out.height,
                    "size_bytes": 0,
                    "has_alpha": out.mime == "image/png",
                    "created_at": out.created_at.isoformat(),
                    "url": out.file_url,
                }
            )

    cur = current_asset_id(document) or (assets_out[0]["id"] if assets_out else "")
    orig = original_asset_id(document) or cur
    can_undo, can_redo = await history_service.can_undo_redo(session, row)
    history_seq = int(getattr(row, "history_seq", 1) or 1)

    return {
        "id": str(row.id),
        "title": row.title or "未命名",
        "revision": history_seq,
        "history_seq": history_seq,
        "original_asset_id": orig,
        "current_asset_id": cur,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "document": normalize_document(document),
        "previous_document": None,
        "assets": assets_out,
        "can_undo": can_undo,
        "can_redo": can_redo,
    }


def to_frontend_asset(out) -> dict[str, Any]:
    """AssetOut → 原仓 Asset。"""
    return {
        "id": str(out.id),
        "kind": "original",
        "source": "upload",
        "image_format": out.mime.split("/")[-1],
        "width": out.width,
        "height": out.height,
        "size_bytes": 0,
        "has_alpha": out.mime == "image/png",
        "created_at": out.created_at.isoformat(),
        "url": out.file_url or asset_file_url(out.id),
    }
