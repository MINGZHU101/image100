"""文生图路由。"""

from uuid import UUID

from fastapi import APIRouter

from app.deps import DbDep
from app.schemas.generation import (
    GenerationCreateIn,
    GenerationCreateOut,
    GenerationRunOut,
    ImageProviderOptionsOut,
)
from app.services import generation as generation_service

router = APIRouter(prefix="/generations", tags=["generations"])


@router.get("/provider-options", response_model=ImageProviderOptionsOut)
async def get_provider_options() -> ImageProviderOptionsOut:
    return generation_service.provider_options()


@router.post("", response_model=GenerationCreateOut)
async def create_generation(body: GenerationCreateIn, db: DbDep) -> GenerationCreateOut:
    return await generation_service.create_generation(
        db,
        prompt=body.prompt,
        width=body.width,
        height=body.height,
        count=body.count,
        image_provider=body.image_provider,
    )


@router.get("/{generation_id}", response_model=GenerationRunOut)
async def get_generation(generation_id: UUID, db: DbDep) -> GenerationRunOut:
    return await generation_service.get_generation(db, generation_id)
