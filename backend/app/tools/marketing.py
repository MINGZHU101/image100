"""营销图工具（mock 可验收）。"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.edits import geometry
from app.models.tool_run import ToolRun
from app.services import runs as runs_service
from app.tools.base import ToolSpec


class MarketingParams(BaseModel):
    kind: str = Field(default="main")
    prompt: str = Field(default="", max_length=1000)


class DeliveryParams(BaseModel):
    ratios: list[str] = Field(default_factory=lambda: ["1:1"])


async def _marketing_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = MarketingParams.model_validate(run.params or {})
    await runs_service.report_progress(session, run, 15, "读取画布")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    await runs_service.report_progress(session, run, 50, f"生成营销图({params.kind})")
    # mock：扩到 1:1 并轻微换底，表示出了一版物料
    output = await asyncio.to_thread(geometry.expand_canvas, source, ratio_w=1, ratio_h=1)
    output = await asyncio.to_thread(
        geometry.replace_background_mock, output, params.prompt or params.kind
    )
    asset_id = await runs_service.write_result_asset(session, run, output, mime="image/png")
    return {"asset_id": str(asset_id), "kind": params.kind}


async def _delivery_handler(session: AsyncSession, run: ToolRun) -> dict[str, Any]:
    params = DeliveryParams.model_validate(run.params or {})
    await runs_service.report_progress(session, run, 20, "读取画布")
    source = await runs_service.load_target_layer_bytes(session, run.session_id)
    ids: list[str] = []
    ratios = params.ratios or ["1:1"]
    for index, ratio in enumerate(ratios):
        parts = ratio.split(":")
        rw, rh = (int(parts[0]), int(parts[1])) if len(parts) == 2 else (1, 1)
        await runs_service.report_progress(
            session, run, 30 + int(60 * (index + 1) / len(ratios)), f"投放尺寸 {ratio}"
        )
        output = await asyncio.to_thread(geometry.expand_canvas, source, ratio_w=rw, ratio_h=rh)
        asset_id = await runs_service.write_result_asset(
            session, run, output, mime="image/png"
        )
        ids.append(str(asset_id))
    return {"asset_ids": ids, "ratios": ratios}


GENERATE_MARKETING = ToolSpec(
    name="generate_marketing",
    label="营销图",
    description="生成营销物料（mock）",
    params_model=MarketingParams,
    handler=_marketing_handler,
)

PREPARE_DELIVERY = ToolSpec(
    name="prepare_delivery_sizes",
    label="投放尺寸",
    description="按比例导出投放尺寸（本地扩图）",
    params_model=DeliveryParams,
    handler=_delivery_handler,
)
