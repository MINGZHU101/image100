"""全站积分/余额流水查询。"""

from datetime import datetime

from fastapi import APIRouter, Query

from app.deps import CurrentAdmin, DbDep
from app.services import admin_ops as admin_ops_service

router = APIRouter()


@router.get("/point-ledgers")
async def point_ledgers(
    _admin: CurrentAdmin,
    db: DbDep,
    q: str | None = None,
    kind: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    rows, total = await admin_ops_service.list_point_ledgers(
        db, q=q, kind=kind, since=since, until=until, page=page, page_size=page_size
    )
    return {
        "items": [
            {
                "id": str(ledger.id),
                "account": account,
                "delta": ledger.delta,
                "balance_after": ledger.balance_after,
                "kind": ledger.kind,
                "remark": ledger.remark or "",
                "created_at": ledger.created_at.isoformat(),
            }
            for ledger, account in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/wallet-ledgers")
async def wallet_ledgers(
    _admin: CurrentAdmin,
    db: DbDep,
    q: str | None = None,
    kind: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    rows, total = await admin_ops_service.list_wallet_ledgers(
        db, q=q, kind=kind, page=page, page_size=page_size
    )
    return {
        "items": [
            {
                "id": str(ledger.id),
                "account": account,
                "delta": ledger.delta,
                "balance_after": ledger.balance_after,
                "kind": ledger.kind,
                "remark": ledger.remark or "",
                "created_at": ledger.created_at.isoformat(),
            }
            for ledger, account in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
