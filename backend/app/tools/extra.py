"""v9 增补工具：裁剪/超分/换背景/扩图/消除/替换/成层/图层变换。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import DEMO_USER_ID
from app.edits import geometry, region_ops
from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.services import runs as runs_service
from app.services import sessions as sessions_service
from app.storage import get_storage
from app.tools.base import ToolSpec


class CropParams(BaseModel):
    rect: dict[str, float] | None = None


class UpscaleParams(BaseModel):
    scale: int = Field(default=2, ge=2, le=4)


class ReplaceBackgroundParams(BaseModel):
    prompt: str = Field(default="", max_length=500)


class ExpandParams(BaseModel):
    ratio: str = Field(default="1:1")


class EraseParams(BaseModel):
    pass


class ReplaceRegionParams(BaseModel):
    prompt: str = Field(default="", max_length=500)


class PromoteParams(BaseModel):
    pass


class LayerIdParams(BaseModel):
    layer_id: str | None = None


class OpacityParams(LayerIdParams):
    opacity: float = Field(ge=0, le=1)


class MoveParams(LayerIdParams):
    x: float = 0
    y: float = 0


class ScaleParams(LayerIdParams):
    scale_x: float = Field(default=1, gt=0, le=8)
    scale_y: float = Field(default=1, gt=0, le=8)
    x: float | None = None
    y: float | None = None


class RotateParams(LayerIdParams):
    rotation: float = Field(default=0, ge=-360, le=360)


class ReorderParams(LayerIdParams):
    place: Literal["top", "bottom", "up", "down"] = "up"


class TextParams(LayerIdParams):
    text: str = Field(default="", max_length=500)
    font_size: float | None = None
    fill: str | None = None


def _parse_ratio(ratio: str) -> tuple[int, int]:
    parts = (ratio or "1:1").split(":")
    if len(parts) != 2:
        return 1, 1
    return max(int(parts[0]), 1), max(int(parts[1]), 1)


async def _require_selection(session: AsyncSession, run: ToolRun) -> dict:
    edit_session = await session.get(EditSession, run.session_id)
    if edit_session is None:
        raise ValueError("会话不存在")
    selection = (edit_session.document or {}).get("selection")
    if not selection:
        raise ValueError("请先框选或涂抹选区")
    return selection


async def _crop_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = CropParams.model_validate(run.params or {})
    if not params.rect:
        raise ValueError("缺少裁剪框")
    await runs_service.report_progress(session, run, 20, "读取图层")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 60, "裁剪")
    output = await asyncio.to_thread(geometry.crop_normalized, source, params.rect)
    asset_id = await runs_service.write_result_asset(session, run, output, mime="image/png")
    return {"asset_id": str(asset_id)}


async def _upscale_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = UpscaleParams.model_validate(run.params or {})
    await runs_service.report_progress(session, run, 20, "读取图层")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 55, "超分")
    output = await asyncio.to_thread(geometry.upscale, source, params.scale)
    asset_id = await runs_service.write_result_asset(session, run, output, mime="image/png")
    return {"asset_id": str(asset_id)}


async def _replace_bg_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = ReplaceBackgroundParams.model_validate(run.params or {})
    await runs_service.report_progress(session, run, 20, "读取图层")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 55, "换背景(mock)")
    output = await asyncio.to_thread(
        geometry.replace_background_mock, source, params.prompt
    )
    asset_id = await runs_service.write_result_asset(session, run, output, mime="image/png")
    return {"asset_id": str(asset_id)}


async def _expand_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = ExpandParams.model_validate(run.params or {})
    rw, rh = _parse_ratio(params.ratio)
    await runs_service.report_progress(session, run, 20, "读取图层")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 55, "扩图")
    output = await asyncio.to_thread(geometry.expand_canvas, source, ratio_w=rw, ratio_h=rh)
    asset_id = await runs_service.write_result_asset(session, run, output, mime="image/png")
    return {"asset_id": str(asset_id)}


async def _erase_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    selection = await _require_selection(session, run)
    await runs_service.report_progress(session, run, 20, "读取选区")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 60, "局部消除")
    output = await asyncio.to_thread(region_ops.erase_region, source, selection)
    asset_id = await runs_service.write_result_asset(session, run, output, mime="image/png")
    await sessions_service.clear_selection(session, run.session_id)
    return {"asset_id": str(asset_id)}


async def _replace_region_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    selection = await _require_selection(session, run)
    params = ReplaceRegionParams.model_validate(run.params or {})
    await runs_service.report_progress(session, run, 20, "读取选区")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 60, "局部替换(mock)")
    output = await asyncio.to_thread(
        region_ops.replace_region, source, selection, params.prompt
    )
    asset_id = await runs_service.write_result_asset(session, run, output, mime="image/png")
    await sessions_service.clear_selection(session, run.session_id)
    return {"asset_id": str(asset_id)}


async def _store_png(session: AsyncSession, data: bytes) -> Asset:
    from PIL import Image
    import io

    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height = image.size
    asset_id = uuid.uuid4()
    storage_key = f"objects/{asset_id}.png"
    get_storage().put(storage_key, data, "image/png")
    asset = Asset(
        id=asset_id,
        owner_id=uuid.UUID(DEMO_USER_ID),
        storage_key=storage_key,
        width=width,
        height=height,
        mime="image/png",
    )
    session.add(asset)
    await session.flush()
    return asset


async def _promote_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    from app.services import history as history_service

    selection = await _require_selection(session, run)
    edit_session = await session.get(EditSession, run.session_id)
    assert edit_session is not None
    await runs_service.report_progress(session, run, 20, "抠选区")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    cut = await asyncio.to_thread(region_ops.cutout_region, source, selection)
    asset = await _store_png(session, cut)

    before = history_service.snapshot_document(edit_session.document)
    document = dict(edit_session.document or {})
    layers = list(document.get("layers") or [])
    new_id = f"layer_promo_{asset.id.hex[:8]}"
    layers.append(
        {
            "id": new_id,
            "name": "选区层",
            "kind": "image",
            "asset_id": str(asset.id),
            "asset_key": asset.storage_key,
            "visible": True,
            "locked": False,
        }
    )
    document["layers"] = layers
    document["active_layer_id"] = new_id
    document["selection"] = None
    document.pop("selection_mask_asset_id", None)
    edit_session.document = document
    flag_modified(edit_session, "document")
    run.result_asset_id = asset.id
    await session.commit()
    await session.refresh(edit_session)
    await history_service.record_edit(
        session,
        edit_session,
        action="promote_object_to_layer",
        params={},
        before=before,
    )
    await runs_service.report_progress(session, run, 95, "成层完成")
    return {"asset_id": str(asset.id), "layer_id": new_id, "active_layer_id": new_id}


def _find_layer(layers: list[dict], layer_id: str | None) -> tuple[int, dict]:
    if layer_id:
        for index, layer in enumerate(layers):
            if str(layer.get("id")) == layer_id:
                return index, dict(layer)
    if not layers:
        raise ValueError("无图层")
    return len(layers) - 1, dict(layers[-1])


async def _mutate_layer_doc(
    session: AsyncSession,
    run: ToolRun,
    *,
    action: str,
    mutate,
) -> dict[str, Any]:
    from app.services import history as history_service

    edit_session = await session.get(EditSession, run.session_id)
    if edit_session is None:
        raise ValueError("会话不存在")
    before = history_service.snapshot_document(edit_session.document)
    document = dict(edit_session.document or {})
    layers = list(document.get("layers") or [])
    document["layers"] = mutate(layers, run.params or {})
    edit_session.document = document
    flag_modified(edit_session, "document")
    await session.commit()
    await session.refresh(edit_session)
    await history_service.record_edit(
        session, edit_session, action=action, params=dict(run.params or {}), before=before
    )
    return {"ok": True}


async def _opacity_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = OpacityParams.model_validate(run.params or {})

    def mutate(layers: list[dict], raw: dict) -> list[dict]:
        index, layer = _find_layer(layers, params.layer_id)
        layer["opacity"] = params.opacity
        layers[index] = layer
        return layers

    return await _mutate_layer_doc(session, run, action="set_layer_opacity", mutate=mutate)


async def _move_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = MoveParams.model_validate(run.params or {})

    def mutate(layers: list[dict], raw: dict) -> list[dict]:
        index, layer = _find_layer(layers, params.layer_id)
        transform = dict(layer.get("transform") or {})
        transform.update({"x": params.x, "y": params.y, "scale_x": transform.get("scale_x", 1), "scale_y": transform.get("scale_y", 1), "rotation": transform.get("rotation", 0)})
        layer["transform"] = transform
        layers[index] = layer
        return layers

    return await _mutate_layer_doc(session, run, action="move_layer", mutate=mutate)


async def _scale_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = ScaleParams.model_validate(run.params or {})

    def mutate(layers: list[dict], raw: dict) -> list[dict]:
        index, layer = _find_layer(layers, params.layer_id)
        transform = dict(layer.get("transform") or {})
        transform["scale_x"] = params.scale_x
        transform["scale_y"] = params.scale_y
        if params.x is not None:
            transform["x"] = params.x
        if params.y is not None:
            transform["y"] = params.y
        transform.setdefault("rotation", 0)
        layer["transform"] = transform
        layers[index] = layer
        return layers

    return await _mutate_layer_doc(session, run, action="scale_layer", mutate=mutate)


async def _rotate_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = RotateParams.model_validate(run.params or {})

    def mutate(layers: list[dict], raw: dict) -> list[dict]:
        index, layer = _find_layer(layers, params.layer_id)
        transform = dict(layer.get("transform") or {})
        transform["rotation"] = params.rotation
        transform.setdefault("x", 0)
        transform.setdefault("y", 0)
        transform.setdefault("scale_x", 1)
        transform.setdefault("scale_y", 1)
        layer["transform"] = transform
        layers[index] = layer
        return layers

    return await _mutate_layer_doc(session, run, action="rotate_layer", mutate=mutate)


async def _reorder_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = ReorderParams.model_validate(run.params or {})

    def mutate(layers: list[dict], raw: dict) -> list[dict]:
        index, layer = _find_layer(layers, params.layer_id)
        layers.pop(index)
        if params.place == "top":
            layers.append(layer)
        elif params.place == "bottom":
            layers.insert(0, layer)
        elif params.place == "up":
            layers.insert(min(index + 1, len(layers)), layer)
        else:
            layers.insert(max(index - 1, 0), layer)
        return layers

    return await _mutate_layer_doc(session, run, action="reorder_layer", mutate=mutate)


async def _text_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = TextParams.model_validate(run.params or {})

    def mutate(layers: list[dict], raw: dict) -> list[dict]:
        index, layer = _find_layer(layers, params.layer_id)
        layer["kind"] = "text"
        layer["text"] = params.text
        if params.font_size is not None:
            layer["font_size"] = params.font_size
        if params.fill is not None:
            layer["fill"] = params.fill
        layers[index] = layer
        return layers

    return await _mutate_layer_doc(session, run, action="set_layer_text", mutate=mutate)


CROP_CANVAS = ToolSpec(
    name="crop_canvas",
    label="裁剪",
    description="按框裁剪当前目标层",
    params_model=CropParams,
    handler=_crop_handler,
)
UPSCALE_IMAGE = ToolSpec(
    name="upscale_image",
    label="超分",
    description="本地放大当前目标层",
    params_model=UpscaleParams,
    handler=_upscale_handler,
)
REPLACE_BACKGROUND = ToolSpec(
    name="replace_background",
    label="换背景",
    description="mock 换背景",
    params_model=ReplaceBackgroundParams,
    handler=_replace_bg_handler,
)
EXPAND_CANVAS = ToolSpec(
    name="expand_canvas",
    label="扩图",
    description="按比例扩展画布",
    params_model=ExpandParams,
    handler=_expand_handler,
)
ERASE_REGION = ToolSpec(
    name="erase_region",
    label="局部消除",
    description="消除选区内内容（本地近似）",
    params_model=EraseParams,
    handler=_erase_handler,
)
REPLACE_REGION = ToolSpec(
    name="replace_region",
    label="局部替换",
    description="mock 替换选区",
    params_model=ReplaceRegionParams,
    handler=_replace_region_handler,
)
PROMOTE_OBJECT = ToolSpec(
    name="promote_object_to_layer",
    label="成层",
    description="把选区提升为新图层",
    params_model=PromoteParams,
    handler=_promote_handler,
)
SET_LAYER_OPACITY = ToolSpec(
    name="set_layer_opacity",
    label="透明度",
    description="设置图层透明度",
    params_model=OpacityParams,
    handler=_opacity_handler,
)
MOVE_LAYER = ToolSpec(
    name="move_layer",
    label="移动图层",
    description="移动图层位置",
    params_model=MoveParams,
    handler=_move_handler,
)
SCALE_LAYER = ToolSpec(
    name="scale_layer",
    label="缩放图层",
    description="缩放图层",
    params_model=ScaleParams,
    handler=_scale_handler,
)
ROTATE_LAYER = ToolSpec(
    name="rotate_layer",
    label="旋转图层",
    description="旋转图层",
    params_model=RotateParams,
    handler=_rotate_handler,
)
REORDER_LAYER = ToolSpec(
    name="reorder_layer",
    label="图层顺序",
    description="调整图层叠放顺序",
    params_model=ReorderParams,
    handler=_reorder_handler,
)
SET_LAYER_TEXT = ToolSpec(
    name="set_layer_text",
    label="改文字",
    description="修改文字层内容",
    params_model=TextParams,
    handler=_text_handler,
)

EXTRA_TOOLS = [
    CROP_CANVAS,
    UPSCALE_IMAGE,
    REPLACE_BACKGROUND,
    EXPAND_CANVAS,
    ERASE_REGION,
    REPLACE_REGION,
    PROMOTE_OBJECT,
    SET_LAYER_OPACITY,
    MOVE_LAYER,
    SCALE_LAYER,
    ROTATE_LAYER,
    REORDER_LAYER,
    SET_LAYER_TEXT,
]
