"""修图类工具：调色、去背。"""

import asyncio
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.edits import pixels
from app.models.tool_run import ToolRun
from app.services import runs as runs_service
from app.tools.base import ToolSpec


class AdjustImageParams(BaseModel):
    brightness: float = Field(default=0.2, ge=-1, le=1)
    contrast: float = Field(default=0.0, ge=-1, le=1)
    saturation: float = Field(default=0.0, ge=-1, le=1)


class RemoveBackgroundParams(BaseModel):
    """去背无额外参数。"""

    pass


async def _adjust_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    await runs_service.report_progress(session, run, 20, "读取图层")
    source = await runs_service.load_main_layer_bytes(session, run.session_id)
    params = AdjustImageParams.model_validate(run.params or {})
    await runs_service.report_progress(session, run, 55, "调整色彩")
    output = await asyncio.to_thread(
        pixels.adjust_image,
        source,
        brightness=params.brightness,
        contrast=params.contrast,
        saturation=params.saturation,
    )
    await runs_service.report_progress(session, run, 85, "写回画布")
    asset_id = await runs_service.write_result_asset(
        session, run, output, mime="image/png"
    )
    return {"asset_id": str(asset_id)}


async def _remove_background_handler(
    session: AsyncSession, run: ToolRun
) -> dict[str, Any]:
    await runs_service.report_progress(session, run, 15, "识别背景色")
    source = await runs_service.load_main_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 50, "去除背景")
    output = await asyncio.to_thread(pixels.mock_remove_background, source)
    await runs_service.report_progress(session, run, 85, "写回画布")
    asset_id = await runs_service.write_result_asset(
        session, run, output, mime="image/png"
    )
    return {"asset_id": str(asset_id)}


ADJUST_IMAGE = ToolSpec(
    name="adjust_image",
    label="提亮",
    description="提高图片亮度（默认 brightness=+0.2）",
    params_model=AdjustImageParams,
    handler=_adjust_handler,
    queued=True,
)

REMOVE_BACKGROUND = ToolSpec(
    name="remove_background",
    label="去背景",
    description="按四角背景色做 mock 去背（透明背景 PNG）",
    params_model=RemoveBackgroundParams,
    handler=_remove_background_handler,
    queued=True,
)
