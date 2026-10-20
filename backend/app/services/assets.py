"""资产用例：上传、列表、读文件。"""

import io
import uuid
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User
from app.models.asset import Asset
from app.schemas.asset import AssetOut
from app.storage import get_storage

# 允许的图片类型
_ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def asset_file_url(asset_id: UUID) -> str:
    return f"/api/assets/{asset_id}/file"


def to_asset_out(asset: Asset) -> AssetOut:
    return AssetOut(
        id=asset.id,
        storage_key=asset.storage_key,
        width=asset.width,
        height=asset.height,
        mime=asset.mime,
        created_at=asset.created_at,
        file_url=asset_file_url(asset.id),
    )


async def upload_asset(session: AsyncSession, user: User, upload: UploadFile) -> AssetOut:
    """校验并保存上传图片，写入磁盘与数据库。"""
    settings = get_settings()
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpeg / png / webp",
        )

    data = await upload.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")
    if len(data) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件超过上限 {settings.upload_max_bytes} 字节",
        )

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            width, height = image.size
            # 统一按实际格式决定后缀，避免伪装扩展名
            format_name = (image.format or "PNG").upper()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法解析为有效图片",
        ) from exc

    ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    ext = ext_map.get(format_name, _ALLOWED_MIME[content_type])
    mime = {
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }[ext]

    asset_id = uuid.uuid4()
    storage_key = f"objects/{asset_id}{ext}"
    storage = get_storage()
    storage.put(storage_key, data, mime)

    asset = Asset(
        id=asset_id,
        owner_id=user.id,
        storage_key=storage_key,
        width=width,
        height=height,
        mime=mime,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return to_asset_out(asset)


async def list_assets(session: AsyncSession, user: User) -> list[AssetOut]:
    result = await session.execute(
        select(Asset)
        .where(Asset.owner_id == user.id)
        .order_by(Asset.created_at.desc())
    )
    rows = result.scalars().all()
    return [to_asset_out(item) for item in rows]


async def get_asset_or_404(
    session: AsyncSession, asset_id: UUID, user: User | None = None
) -> Asset:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资产不存在")
    if user is not None and asset.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资产不存在")
    return asset
