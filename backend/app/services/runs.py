"""工具运行态：进度上报、读写主图层、写回结果资产。"""

import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import DEMO_USER_ID
from app.events import publish_event
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


async def load_main_layer_bytes(session: AsyncSession, session_id: UUID) -> bytes:
    """读取会话主图层图片字节。"""
    edit_session = await session.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    layers = (edit_session.document or {}).get("layers") or []
    if not layers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="会话无图层")
    main = layers[0]
    asset_id = UUID(str(main["asset_id"]))
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图层资产不存在")
    storage = get_storage()
    if not storage.exists(asset.storage_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图层文件不存在")
    return storage.get(asset.storage_key)


async def write_result_asset(
    session: AsyncSession,
    run: ToolRun,
    data: bytes,
    *,
    mime: str,
) -> UUID:
    """写出新资产，并更新会话 document 主图层指向。"""
    from PIL import Image
    import io

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
    canvas["width"] = width
    canvas["height"] = height
    layers = list(document.get("layers") or [])
    if layers:
        main = dict(layers[0])
        main["asset_id"] = str(asset_id)
        main["asset_key"] = storage_key
        layers[0] = main
    else:
        layers = [
            {
                "id": "layer_main",
                "name": "主图层",
                "asset_id": str(asset_id),
                "asset_key": storage_key,
                "visible": True,
            }
        ]
    document["canvas"] = canvas
    document["layers"] = layers
    document["version"] = document.get("version", 1)
    edit_session.document = document
    # JSONB 赋值后显式标记，确保变更被刷库
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
