"""图层类工具：主体/背景拆层。"""

import asyncio
import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.edits import split as split_edits
from app.layers import (
    LAYER_MAIN_ID,
    LAYER_SUBJECT_ID,
    already_split,
    build_split_layers,
)
from app.models.asset import Asset
from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.services import runs as runs_service
from app.storage import get_storage
from app.tools.base import ToolSpec


class SplitLayersParams(BaseModel):
    """拆层参数；force 预留，v7 默认忽略（已拆则跳过）。"""

    force: bool = Field(default=False)


async def _store_png(session: AsyncSession, data: bytes, owner_id: uuid.UUID) -> Asset:
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
        owner_id=owner_id,
        storage_key=storage_key,
        width=width,
        height=height,
        mime="image/png",
    )
    session.add(asset)
    await session.flush()
    return asset


async def _split_layers_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    edit_session = await session.get(EditSession, run.session_id)
    if edit_session is None:
        raise ValueError("会话不存在")

    document = dict(edit_session.document or {})
    if already_split(document):
        await runs_service.report_progress(session, run, 100, "已拆层，跳过")
        return {"skipped": True, "reason": "already_split"}

    await runs_service.report_progress(session, run, 20, "读取画布")
    # 未拆层：读主图层（兼容只有一层的会话）
    layers = list(document.get("layers") or [])
    if not layers:
        raise ValueError("会话无图层")
    source_layer = next(
        (layer for layer in layers if str(layer.get("id")) == LAYER_MAIN_ID),
        layers[0],
    )
    source = await runs_service.load_layer_bytes_by_id(
        session, run.session_id, str(source_layer["id"])
    )

    await runs_service.report_progress(session, run, 45, "分离主体")
    subject_png, background_png = await asyncio.to_thread(
        split_edits.split_to_subject_background, source
    )

    await runs_service.report_progress(session, run, 70, "写入图层资产")
    background_asset = await _store_png(session, background_png, edit_session.owner_id)
    subject_asset = await _store_png(session, subject_png, edit_session.owner_id)

    from app.services import history as history_service

    before = history_service.snapshot_document(edit_session.document)
    document["layers"] = build_split_layers(
        background_asset_id=str(background_asset.id),
        background_key=background_asset.storage_key,
        subject_asset_id=str(subject_asset.id),
        subject_key=subject_asset.storage_key,
    )
    document["active_layer_id"] = LAYER_SUBJECT_ID
    document["selection"] = None
    document["version"] = document.get("version", 1)
    edit_session.document = document
    flag_modified(edit_session, "document")
    run.result_asset_id = subject_asset.id
    await session.commit()
    await session.refresh(edit_session)
    await history_service.record_edit(
        session,
        edit_session,
        action="split_layers",
        params=dict(run.params or {}),
        before=before,
    )

    await runs_service.report_progress(session, run, 95, "拆层完成")
    return {
        "skipped": False,
        "asset_ids": [str(background_asset.id), str(subject_asset.id)],
        "active_layer_id": LAYER_SUBJECT_ID,
    }


SPLIT_LAYERS = ToolSpec(
    name="split_layers",
    label="拆层",
    description="把画面拆成背景和主体两层；已拆过则跳过",
    params_model=SplitLayersParams,
    handler=_split_layers_handler,
    queued=True,
    ui_exposed=True,
    agent_exposed=True,
)
