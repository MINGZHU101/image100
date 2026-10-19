"""局部选区工具：仅对选区内做调色。"""

import asyncio
import io
from typing import Any

from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.edits import mask as mask_edits
from app.edits import pixels
from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.services import runs as runs_service
from app.services import sessions as sessions_service
from app.tools.base import ToolSpec


class AdjustRegionParams(BaseModel):
    """局部调色参数，与整图提亮一致。"""

    brightness: float = Field(default=0.2, ge=-1, le=1)
    contrast: float = Field(default=0.0, ge=-1, le=1)
    saturation: float = Field(default=0.0, ge=-1, le=1)


async def _adjust_region_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    await runs_service.report_progress(session, run, 15, "读取选区")
    edit_session = await session.get(EditSession, run.session_id)
    if edit_session is None:
        raise ValueError("会话不存在")

    selection = (edit_session.document or {}).get("selection")
    if not selection:
        raise ValueError("请先框选或涂抹选区")

    await runs_service.report_progress(session, run, 30, "读取图层")
    source = await runs_service.load_main_layer_bytes(session, run.session_id)
    params = AdjustRegionParams.model_validate(run.params or {})

    canvas = (edit_session.document or {}).get("canvas") or {}
    width = int(canvas.get("width") or 0)
    height = int(canvas.get("height") or 0)
    if width <= 0 or height <= 0:
        # 回退到源图尺寸
        with Image.open(io.BytesIO(source)) as image:
            width, height = image.size

    await runs_service.report_progress(session, run, 45, "生成选区掩膜")
    region_mask = await asyncio.to_thread(
        mask_edits.mask_from_selection,
        (width, height),
        selection,
    )

    await runs_service.report_progress(session, run, 60, "局部调色")
    edited = await asyncio.to_thread(
        pixels.adjust_image,
        source,
        brightness=params.brightness,
        contrast=params.contrast,
        saturation=params.saturation,
    )
    await runs_service.report_progress(session, run, 80, "合并选区")
    output = await asyncio.to_thread(
        mask_edits.apply_masked,
        source,
        edited,
        region_mask,
    )
    await runs_service.report_progress(session, run, 90, "写回画布")
    asset_id = await runs_service.write_result_asset(
        session, run, output, mime="image/png"
    )
    # 成功后自动清空选区，避免下次误用
    await sessions_service.clear_selection(session, run.session_id)
    return {"asset_id": str(asset_id)}



ADJUST_REGION = ToolSpec(
    name="adjust_region",
    label="局部提亮",
    description="仅对当前选区内提高亮度（默认 brightness=+0.2）；无选区时请先框选",
    params_model=AdjustRegionParams,
    handler=_adjust_region_handler,
    queued=True,
    ui_exposed=True,
    agent_exposed=True,
)
