"""等待 PostgreSQL 就绪（Docker 启动用）。"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings


async def main() -> int:
    url = get_settings().database_url
    last_error = ""
    for attempt in range(1, 61):
        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print(f"database ready (attempt {attempt})")
            return 0
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            print(f"waiting database… ({attempt}/60) {last_error[:120]}")
            await asyncio.sleep(2)
        finally:
            await engine.dispose()
    print(f"database not ready: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
