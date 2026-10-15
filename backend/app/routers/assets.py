"""资产路由：上传、列表、取文件。"""

from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from app.deps import DbDep
from app.schemas.asset import AssetListOut, AssetOut
from app.services import assets as assets_service
from app.storage import get_storage

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetOut)
async def upload_asset(
    db: DbDep,
    file: UploadFile = File(...),
) -> AssetOut:
    """multipart 字段名：file。"""
    return await assets_service.upload_asset(db, file)


@router.get("", response_model=AssetListOut)
async def list_assets(db: DbDep) -> AssetListOut:
    items = await assets_service.list_assets(db)
    return AssetListOut(items=items)


@router.get("/{asset_id}/file")
async def get_asset_file(asset_id: UUID, db: DbDep) -> FileResponse:
    """返回图片二进制，供画布 <img> / Konva 加载。"""
    asset = await assets_service.get_asset_or_404(db, asset_id)
    storage = get_storage()
    if not storage.exists(asset.storage_key):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )
    path = storage.absolute_path(asset.storage_key)
    return FileResponse(path, media_type=asset.mime, filename=path.name)
