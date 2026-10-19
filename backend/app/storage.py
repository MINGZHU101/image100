"""对象存储：local 与腾讯云 COS 可切换。"""

from pathlib import Path
from typing import Protocol

from app.config import get_settings


class Storage(Protocol):
    """存储后端协议。"""

    def ensure_ready(self) -> None:
        """确保存储可用。"""

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
        del content_type
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


class CosStorage:
    """腾讯云 COS 实现（cos-python-sdk-v5）。"""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.cos_secret_id or not settings.cos_secret_key:
            raise RuntimeError("COS 模式需要 COS_SECRET_ID / COS_SECRET_KEY")
        if not settings.cos_bucket:
            raise RuntimeError("COS 模式需要 COS_BUCKET（完整名，含 APPID）")
        # 延迟导入，避免 local 模式强制依赖 SDK
        from qcloud_cos import CosConfig, CosS3Client

        config = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key,
        )
        self._client = CosS3Client(config)
        self._bucket = settings.cos_bucket
        self._region = settings.cos_region

    def ensure_ready(self) -> None:
        # head bucket 验证连通
        self._client.head_bucket(Bucket=self._bucket)

    def _object_key(self, key: str) -> str:
        return key.replace("\\", "/").lstrip("/")

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Body=data,
            Key=self._object_key(key),
            ContentType=content_type or "application/octet-stream",
        )

    def get(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=self._bucket,
            Key=self._object_key(key),
        )
        body = response["Body"]
        return body.get_raw_stream().read()

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._object_key(key))
            return True
        except Exception:
            return False

    def absolute_path(self, key: str) -> Path:
        raise NotImplementedError("COS 无本地绝对路径，请用 get() 读字节")

    def check_writable(self) -> str:
        """写入探测对象再删除。"""
        probe_key = "objects/.health_write_probe"
        try:
            self.put(probe_key, b"ok", "text/plain")
            self._client.delete_object(Bucket=self._bucket, Key=self._object_key(probe_key))
            return "ok"
        except Exception:
            return "error"


_storage: Storage | None = None


def get_storage() -> Storage:
    """进程内存储单例。"""
    global _storage
    if _storage is None:
        settings = get_settings()
        backend = settings.storage_backend.strip().lower()
        if backend == "local":
            _storage = LocalStorage()
        elif backend == "cos":
            _storage = CosStorage()
        else:
            raise RuntimeError(f"不支持的 STORAGE_BACKEND={settings.storage_backend}")
        _storage.ensure_ready()
    return _storage
