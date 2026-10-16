"""画布几何类工具：翻转。"""

import asyncio
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.edits import pixels
from app.models.tool_run import ToolRun
from app.services import runs as runs_service
from app.tools.base import ToolSpec


class FlipLayerParams(BaseModel):
    """水平翻转，无额外参数。"""

    pass


async def _flip_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    await runs_service.report_progress(session, run, 25, "读取图层")
    source = await runs_service.load_main_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 60, "水平翻转")
    output = await asyncio.to_thread(pixels.flip_horizontal, source)
    await runs_service.report_progress(session, run, 90, "写回画布")
    asset_id = await runs_service.write_result_asset(
        session, run, output, mime="image/png"
    )
    return {"asset_id": str(asset_id)}


FLIP_LAYER = ToolSpec(
    name="flip_layer",
    label="水平翻转",
    description="将主图层水平镜像翻转",
    params_model=FlipLayerParams,
    handler=_flip_handler,
    queued=True,
)
