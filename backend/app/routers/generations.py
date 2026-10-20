"""文生图路由（含原仓 GenerateInput 兼容）。"""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.deps import CurrentUser, DbDep
from app.membership_rules import COST_GENERATION
from app.schemas.generation import GenerationRunOut, ImageProviderOptionsOut
from app.services import billing
from app.services import generation as generation_service
from app.services import tools as tools_service

router = APIRouter(prefix="/generations", tags=["generations"])

_RATIO_SIZE: dict[str, tuple[int, int]] = {
    "1:1": (1024, 1024),
    "4:5": (1024, 1280),
    "3:4": (960, 1280),
    "9:16": (720, 1280),
    "16:9": (1280, 720),
}


class GenerateCompatIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    ratio: str | None = None
    count: int = Field(default=2, ge=1, le=4)
    negative_prompt: str | None = None
    reference_asset_ids: list[UUID] | None = None
    width: int | None = None
    height: int | None = None
    image_provider: Literal["mock", "dashscope"] | None = None


@router.get("/provider-options", response_model=ImageProviderOptionsOut)
async def get_provider_options() -> ImageProviderOptionsOut:
    return generation_service.provider_options()


@router.post("")
async def create_generation(
    body: GenerateCompatIn, db: DbDep, user: CurrentUser
) -> dict[str, Any]:
    """创建后返回原仓 Run 形状，便于 Create/Candidates 页直接订阅。"""
    if body.width and body.height:
        width, height = body.width, body.height
    else:
        width, height = _RATIO_SIZE.get(body.ratio or "1:1", (1024, 1024))
    await billing.charge_ai_operation(
        db,
        user,
        cost=COST_GENERATION,
        kind="consume_generation",
        remark="文生图",
    )
    created = await generation_service.create_generation(
        db,
        user,
        prompt=body.prompt,
        width=width,
        height=height,
        count=body.count,
        image_provider=body.image_provider,
    )
    return await tools_service.get_run_compat(db, created.generation_id)


@router.get("/{generation_id}", response_model=GenerationRunOut)
async def get_generation(generation_id: UUID, db: DbDep) -> GenerationRunOut:
    return await generation_service.get_generation(db, generation_id)
