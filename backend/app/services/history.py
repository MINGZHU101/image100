"""会话编辑历史：追加快照、undo/redo、列表。"""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.edit_history import HISTORY_LIMIT, EditHistory
from app.models.edit_session import EditSession


def snapshot_document(document: dict[str, Any] | None) -> dict[str, Any]:
    return copy.deepcopy(document or {})


async def _max_seq(session: AsyncSession, session_id: UUID) -> int:
    result = await session.execute(
        select(func.max(EditHistory.seq)).where(EditHistory.session_id == session_id)
    )
    value = result.scalar()
    return int(value or 0)


async def _entry(
    session: AsyncSession, session_id: UUID, seq: int
) -> EditHistory | None:
    result = await session.execute(
        select(EditHistory).where(
            EditHistory.session_id == session_id,
            EditHistory.seq == seq,
        )
    )
    return result.scalar_one_or_none()


async def ensure_initial_history(session: AsyncSession, row: EditSession) -> None:
    """新建会话后写入 seq=1 基线快照。"""
    existing = await _entry(session, row.id, 1)
    if existing is not None:
        return
    session.add(
        EditHistory(
            owner_id=row.owner_id,
            session_id=row.id,
            seq=1,
            action="create_session",
            params={},
            result={"document": snapshot_document(row.document)},
        )
    )
    row.history_seq = 1
    await session.commit()
    await session.refresh(row)


async def record_edit(
    session: AsyncSession,
    row: EditSession,
    *,
    action: str,
    params: dict[str, Any] | None = None,
    before: dict[str, Any] | None = None,
) -> EditSession:
    """
    在 document 已更新后调用：截断 redo 分支，追加一条历史。
    before 缺省时用当前库内上一指针的 result.document（不推荐）；调用方应传入变更前快照。
    """
    before_doc = before if before is not None else snapshot_document(row.document)

    await session.execute(
        delete(EditHistory).where(
            EditHistory.session_id == row.id,
            EditHistory.seq > row.history_seq,
        )
    )

    seq = int(row.history_seq or 1) + 1
    session.add(
        EditHistory(
            owner_id=row.owner_id,
            session_id=row.id,
            seq=seq,
            action=action,
            params={**(params or {}), "before": {"document": before_doc}},
            result={"document": snapshot_document(row.document)},
        )
    )
    await session.execute(
        delete(EditHistory).where(
            EditHistory.session_id == row.id,
            EditHistory.seq <= seq - HISTORY_LIMIT,
        )
    )
    row.history_seq = seq
    await session.commit()
    await session.refresh(row)
    return row


async def can_undo_redo(session: AsyncSession, row: EditSession) -> tuple[bool, bool]:
    max_seq = await _max_seq(session, row.id)
    return row.history_seq > 1, max_seq > row.history_seq


async def list_history(session: AsyncSession, session_id: UUID) -> list[dict[str, Any]]:
    result = await session.execute(
        select(EditHistory)
        .where(EditHistory.session_id == session_id)
        .order_by(EditHistory.seq.asc())
    )
    items: list[dict[str, Any]] = []
    for row in result.scalars().all():
        items.append(
            {
                "seq": row.seq,
                "action": row.action,
                "params": {k: v for k, v in (row.params or {}).items() if k != "before"},
                "result": {
                    k: v for k, v in (row.result or {}).items() if k != "document"
                },
                "created_at": row.created_at.isoformat(),
            }
        )
    return items


async def undo(session: AsyncSession, session_id: UUID) -> EditSession:
    row = await session.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if row.history_seq <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可撤销的操作")
    entry = await _entry(session, session_id, row.history_seq)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="历史记录缺失")
    before = (entry.params or {}).get("before") or {}
    document = before.get("document")
    if document is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法撤销：缺少快照")
    row.document = document
    flag_modified(row, "document")
    row.history_seq -= 1
    await session.commit()
    await session.refresh(row)
    return row


async def redo(session: AsyncSession, session_id: UUID) -> EditSession:
    row = await session.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    entry = await _entry(session, session_id, row.history_seq + 1)
    if entry is None or "document" not in (entry.result or {}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可重做的操作")
    row.document = entry.result["document"]
    flag_modified(row, "document")
    row.history_seq += 1
    await session.commit()
    await session.refresh(row)
    return row
