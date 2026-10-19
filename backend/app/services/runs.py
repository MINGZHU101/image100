"""工具运行态：进度上报、按目标层读写、写回结果资产。"""

import io
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import DEMO_USER_ID
from app.edits import split as split_edits
from app.events import publish_event
from app.layers import resolve_target_layer
from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.storage import get_storage


async def load_run(session: AsyncSession, run_id: UUID) -> ToolRun:
    run = await session.get(ToolRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行不存在")
    return run


async def report_progress(
    session: AsyncSession,
    run: ToolRun,
    progress: int,
    message: str,
) -> None:
    """更新进度并推送 SSE 事件。"""
    run.progress = max(0, min(100, progress))
    run.status = "running"
    await session.commit()
    await publish_event(
        run.id,
        {
            "event": "progress",
            "run_id": str(run.id),
            "progress": run.progress,
            "message": message,
        },
    )


async def _load_asset_bytes(session: AsyncSession, asset_id: UUID) -> bytes:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图层资产不存在")
    storage = get_storage()
    if not storage.exists(asset.storage_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图层文件不存在")
    return storage.get(asset.storage_key)


async def load_target_layer_bytes(session: AsyncSession, session_id: UUID) -> bytes:
    """读取当前编辑目标层（active 或最上层可见）。"""
    edit_session = await session.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    try:
        target = resolve_target_layer(edit_session.document)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return await _load_asset_bytes(session, UUID(str(target["asset_id"])))


async def load_main_layer_bytes(session: AsyncSession, session_id: UUID) -> bytes:
    """兼容旧名：等价于加载目标层。"""
    return await load_target_layer_bytes(session, session_id)


async def load_layer_bytes_by_id(
    session: AsyncSession, session_id: UUID, layer_id: str
) -> bytes:
    edit_session = await session.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    layers = (edit_session.document or {}).get("layers") or []
    for layer in layers:
        if str(layer.get("id")) == layer_id:
            return await _load_asset_bytes(session, UUID(str(layer["asset_id"])))
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图层不存在")


async def flatten_visible_layers(session: AsyncSession, session_id: UUID) -> bytes:
    """按可见层自下而上合成，用于导出。"""
    edit_session = await session.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    document = edit_session.document or {}
    layers = list(document.get("layers") or [])
    if not layers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="会话无图层")

    canvas = document.get("canvas") or {}
    width = int(canvas.get("width") or 0)
    height = int(canvas.get("height") or 0)

    images: list[bytes] = []
    for layer in layers:
        if not layer.get("visible", True):
            continue
        data = await _load_asset_bytes(session, UUID(str(layer["asset_id"])))
        images.append(data)
        if width <= 0 or height <= 0:
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size

    if not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="没有可见图层可导出"
        )
    if len(images) == 1:
        return images[0]
    return split_edits.composite_layers(images, (width, height))


async def write_result_asset(
    session: AsyncSession,
    run: ToolRun,
    data: bytes,
    *,
    mime: str,
    layer_id: str | None = None,
) -> UUID:
    """写出新资产，并更新目标图层（默认 active / 最上层可见）的 asset 指向。"""
    edit_session = await session.get(EditSession, run.session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height = image.size

    asset_id = uuid.uuid4()
    ext = ".png" if mime == "image/png" else ".jpg"
    storage_key = f"objects/{asset_id}{ext}"
    get_storage().put(storage_key, data, mime)

    asset = Asset(
        id=asset_id,
        owner_id=UUID(DEMO_USER_ID),
        storage_key=storage_key,
        width=width,
        height=height,
        mime=mime,
    )
    session.add(asset)

    document = dict(edit_session.document or {})
    canvas = dict(document.get("canvas") or {})
    # 仅单层会话时同步画布尺寸；多层拆层后保持原画布，避免主体透明图缩小画布
    layers = list(document.get("layers") or [])
    target_id = layer_id
    if not target_id:
        try:
            target_id = str(resolve_target_layer(document).get("id"))
        except ValueError:
            target_id = None

    updated = False
    new_layers: list[dict] = []
    for layer in layers:
        item = dict(layer)
        if target_id and str(item.get("id")) == target_id:
            item["asset_id"] = str(asset_id)
            item["asset_key"] = storage_key
            updated = True
        new_layers.append(item)

    if not updated:
        if len(new_layers) == 1:
            only = dict(new_layers[0])
            only["asset_id"] = str(asset_id)
            only["asset_key"] = storage_key
            new_layers[0] = only
            canvas["width"] = width
            canvas["height"] = height
        elif not new_layers:
            new_layers = [
                {
                    "id": "layer_main",
                    "name": "主图层",
                    "asset_id": str(asset_id),
                    "asset_key": storage_key,
                    "visible": True,
                }
            ]
            canvas["width"] = width
            canvas["height"] = height
        else:
            # 多层且未命中：更新最上层可见
            for index in range(len(new_layers) - 1, -1, -1):
                if new_layers[index].get("visible", True):
                    new_layers[index] = dict(new_layers[index])
                    new_layers[index]["asset_id"] = str(asset_id)
                    new_layers[index]["asset_key"] = storage_key
                    break

    if len(new_layers) == 1:
        canvas["width"] = width
        canvas["height"] = height

    document["canvas"] = canvas
    document["layers"] = new_layers
    document["version"] = document.get("version", 1)
    edit_session.document = document
    flag_modified(edit_session, "document")

    run.result_asset_id = asset_id
    await session.commit()
    return asset_id


async def mark_succeeded(session: AsyncSession, run: ToolRun) -> None:
    run.status = "succeeded"
    run.progress = 100
    run.finished_at = datetime.now(timezone.utc)
    await session.commit()
    await publish_event(
        run.id,
        {
            "event": "completed",
            "run_id": str(run.id),
            "session_id": str(run.session_id),
            "asset_id": str(run.result_asset_id) if run.result_asset_id else None,
        },
    )


async def mark_failed(session: AsyncSession, run: ToolRun, message: str) -> None:
    run.status = "failed"
    run.error = message
    run.finished_at = datetime.now(timezone.utc)
    await session.commit()
    await publish_event(
        run.id,
        {
            "event": "error",
            "run_id": str(run.id),
            "message": message,
        },
    )
