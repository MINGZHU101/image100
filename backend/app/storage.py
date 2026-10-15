"""本地文件存储：协议可扩展，v2 仅实现 local。"""

from pathlib import Path
from typing import Protocol

from app.config import get_settings


class Storage(Protocol):
    """存储后端协议，便于后续切换腾讯云 COS。"""

    def ensure_ready(self) -> None:
        """确保存储可用（建目录等）。"""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """写入对象。"""

    def get(self, key: str) -> bytes:
        """读取对象。"""

    def exists(self, key: str) -> bool:
        """对象是否存在。"""

    def absolute_path(self, key: str) -> Path:
        """本地绝对路径（仅 local 有意义）。"""

    def check_writable(self) -> str:
        """连通/可写探测：ok 或 error。"""


class LocalStorage:
    """项目根 data/ 下的本地磁盘实现。"""

    def __init__(self, root: Path | None = None) -> None:
        settings = get_settings()
        self._root = root or settings.storage_root

    def ensure_ready(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "objects").mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # 禁止路径穿越
        cleaned = key.replace("\\", "/").lstrip("/")
        target = (self._root / cleaned).resolve()
        if not str(target).startswith(str(self._root.resolve())):
            raise ValueError("非法 storage key")
        return target

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def absolute_path(self, key: str) -> Path:
        return self._resolve(key)

    def check_writable(self) -> str:
        """写临时文件再删除，验证目录可写。"""
        try:
            self.ensure_ready()
            probe = self._root / ".health_write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return "ok"
        except Exception:
            return "error"


_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    """进程内存储单例。"""
    global _storage
    if _storage is None:
        settings = get_settings()
        if settings.storage_backend != "local":
            raise RuntimeError(
                f"v2 仅支持 local 存储，当前 STORAGE_BACKEND={settings.storage_backend}"
            )
        _storage = LocalStorage()
        _storage.ensure_ready()
    return _storage
