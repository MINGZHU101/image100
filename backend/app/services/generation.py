"""文生图用例：落库、入队、写资产。"""

import io
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import get_settings
from app.events import publish_event
from app.models import User
from app.models.asset import Asset
from app.models.generation_run import GenerationRun
from app.providers.image import ImageProviderError, get_image_provider
from app.queue import enqueue_generation
from app.schemas.generation import (
    GenerationCreateOut,
    GenerationRunOut,
    ImageProviderOptionsOut,
)
from app.storage import get_storage


def provider_options() -> ImageProviderOptionsOut:
    settings = get_settings()
    default = settings.image_provider.strip().lower()
    if default not in ("mock", "dashscope"):
        default = "dashscope"
    has_key = bool(settings.dashscope_api_key)
    models = list(settings.text_to_image_models or [])
    if settings.text_to_image_model and settings.text_to_image_model not in models:
        models.insert(0, settings.text_to_image_model)
    return ImageProviderOptionsOut(
        default_provider=default if default == "mock" or has_key else "mock",
        dashscope_available=has_key,
        providers=["mock", "dashscope"],
        default_image_model=settings.text_to_image_model,
        image_models=models,
    )


def resolve_image_model(requested: str | None) -> str:
    """校验请求模型是否在白名单；非法则回落默认。"""
    settings = get_settings()
    allowed = set(settings.text_to_image_models or [])
    allowed.add(settings.text_to_image_model)
    name = (requested or settings.text_to_image_model or "").strip()
    if name in allowed:
        return name
    return settings.text_to_image_model


def _resolve_provider(requested: str | None) -> str:
    settings = get_settings()
    name = (requested or settings.image_provider or "dashscope").strip().lower()
    if name not in ("mock", "dashscope"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_provider 仅支持 mock 或 dashscope",
        )
    if name == "dashscope" and not settings.dashscope_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置 DASHSCOPE_API_KEY，请切换到 Mock 生图",
        )
    return name


def _to_out(row: GenerationRun) -> GenerationRunOut:
    return GenerationRunOut(
        id=row.id,
        prompt=row.prompt,
        params=row.params or {},
        image_provider=row.image_provider,
        status=row.status,
        progress=row.progress,
        result_asset_ids=[str(item) for item in (row.result_asset_ids or [])],
        error=row.error,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


async def create_generation(
    session: AsyncSession,
    user: User,
    *,
    prompt: str,
    width: int,
    height: int,
    count: int,
    image_provider: str | None,
    image_model: str | None = None,
) -> GenerationCreateOut:
    provider = _resolve_provider(image_provider)
    model_name = resolve_image_model(image_model)
    row = GenerationRun(
        owner_id=user.id,
        prompt=prompt.strip(),
        params={
            "width": width,
            "height": height,
            "count": count,
            "image_model": model_name,
        },
        image_provider=provider,
        status="queued",
        progress=0,
        result_asset_ids=[],
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    try:
        await enqueue_generation(row.id)
    except Exception as exc:  # noqa: BLE001
        row.status = "failed"
        row.error = f"入队失败: {exc}"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"生图入队失败: {exc}",
        ) from exc
    return GenerationCreateOut(generation_id=row.id, status="queued")


async def get_generation(session: AsyncSession, generation_id: UUID) -> GenerationRunOut:
    row = await session.get(GenerationRun, generation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="生图任务不存在")
    return _to_out(row)


async def execute_generation(session: AsyncSession, generation_id: UUID) -> dict:
    """Worker：调用 Provider，写入 assets，推送进度。"""
    row = await session.get(GenerationRun, generation_id)
    if row is None:
        return {"ok": False, "error": "not_found"}

    row.status = "running"
    row.progress = 10
    await session.commit()
    await publish_event(
        row.id,
        {"event": "progress", "run_id": str(row.id), "progress": 10, "message": "开始生成"},
    )

    params = dict(row.params or {})
    width = int(params.get("width") or 1024)
    height = int(params.get("height") or 1024)
    count = int(params.get("count") or 1)
    try:
        provider = get_image_provider(row.image_provider)
        image_model = resolve_image_model(
            str(params.get("image_model") or "") or None
        )
        params["image_model"] = image_model
        # count≥2：先改写/扩写提示词，再逐张生成，避免同 prompt 雷同
        if count >= 2:
            from app.services.prompt_variants import build_prompt_variants

            variants = await build_prompt_variants(row.prompt, count)
            params["prompt_variants"] = variants
            row.params = params
            flag_modified(row, "params")
            await session.commit()
            images: list[bytes] = []
            for index, variant in enumerate(variants):
                part = await provider.generate(
                    prompt=variant,
                    width=width,
                    height=height,
                    count=1,
                    model=image_model,
                )
                images.extend(part)
                progress = 10 + int(10 * (index + 1) / max(count, 1))
                row.progress = progress
                await session.commit()
                await publish_event(
                    row.id,
                    {
                        "event": "progress",
                        "run_id": str(row.id),
                        "progress": progress,
                        "message": f"正在生成第 {index + 1}/{count} 张",
                    },
                )
        else:
            images = await provider.generate(
                prompt=row.prompt,
                width=width,
                height=height,
                count=1,
                model=image_model,
            )
    except ImageProviderError as exc:
        row.status = "failed"
        row.error = str(exc)
        row.finished_at = datetime.now(timezone.utc)
        await session.commit()
        await publish_event(
            row.id,
            {"event": "error", "run_id": str(row.id), "message": str(exc)},
        )
        return {"ok": False, "error": str(exc)}

    asset_ids: list[str] = []
    storage = get_storage()
    for index, data in enumerate(images):
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            width, height = image.size
        asset_id = uuid.uuid4()
        storage_key = f"objects/{asset_id}.png"
        storage.put(storage_key, data, "image/png")
        owner_id = row.owner_id
        if owner_id is None:
            from app.config import DEMO_USER_ID

            owner_id = UUID(DEMO_USER_ID)
        session.add(
            Asset(
                id=asset_id,
                owner_id=owner_id,
                storage_key=storage_key,
                width=width,
                height=height,
                mime="image/png",
            )
        )
        asset_ids.append(str(asset_id))
        progress = 20 + int(70 * (index + 1) / max(len(images), 1))
        row.progress = progress
        row.result_asset_ids = asset_ids
        flag_modified(row, "result_asset_ids")
        await session.commit()
        await publish_event(
            row.id,
            {
                "event": "progress",
                "run_id": str(row.id),
                "progress": progress,
                "message": f"已生成 {index + 1}/{len(images)}",
            },
        )

    row.status = "succeeded"
    row.progress = 100
    row.finished_at = datetime.now(timezone.utc)
    await session.commit()
    await publish_event(
        row.id,
        {
            "event": "completed",
            "run_id": str(row.id),
            "asset_ids": asset_ids,
        },
    )
    return {"ok": True, "asset_ids": asset_ids}
