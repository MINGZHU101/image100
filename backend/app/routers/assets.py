"""资产路由：上传、列表、取文件。"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.compat.session_detail import to_frontend_asset
from app.deps import DbDep
from app.schemas.asset import AssetOut
from app.services import assets as assets_service
from app.storage import get_storage

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("")
async def upload_asset(
    db: DbDep,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """multipart 字段名：file；响应对齐原仓 Asset。"""
    out = await assets_service.upload_asset(db, file)
    return to_frontend_asset(out)


@router.get("")
async def list_assets(db: DbDep, limit: int = 50) -> list[dict[str, Any]]:
    del limit
    items = await assets_service.list_assets(db)
    return [to_frontend_asset(item) for item in items]


@router.get("/library")
async def asset_library(db: DbDep, limit: int = 50) -> list[dict[str, Any]]:
    """原仓素材库：本期用扁平资产列表拼一组。"""
    del limit
    items = await assets_service.list_assets(db)
    if not items:
        return []
    assets = [to_frontend_asset(item) for item in items]
    cover = assets[0]
    return [
        {
            "session_id": None,
            "title": "最近上传",
            "updated_at": cover["created_at"],
            "cover": cover,
            "assets": assets,
        }
    ]


@router.get("/{asset_id}/file")
async def get_asset_file(asset_id: UUID, db: DbDep) -> Response:
    """返回图片二进制（local / COS 统一走 storage.get）。"""
    asset = await assets_service.get_asset_or_404(db, asset_id)
    storage = get_storage()
    if not storage.exists(asset.storage_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    data = storage.get(asset.storage_key)
    return Response(content=data, media_type=asset.mime)
