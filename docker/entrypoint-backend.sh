#!/bin/sh
set -e

echo "[entrypoint] wait for database…"
python -m scripts.wait_for_db

# 仅 API 容器跑迁移，避免与 Worker 并发升级
if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
  echo "[entrypoint] alembic upgrade head…"
  alembic upgrade head
else
  echo "[entrypoint] skip migrations"
fi

echo "[entrypoint] exec: $*"
exec "$@"
