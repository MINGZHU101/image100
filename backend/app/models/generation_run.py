"""文生图任务记录。"""

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TIMESTAMPTZ, UUIDBase


class GenerationRun(UUIDBase):
    __tablename__ = "generation_runs"

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    image_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    # queued | running | succeeded | failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_asset_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
