"""Local-filesystem storage backend — preserves the original behaviour for
dev / docker-compose / single-host on-prem deployments.

Files land under ``UPLOAD_DIR`` (defaults to ``./uploads``, overridable via
env). Path traversal is checked at the route layer; this class trusts that
the filename has already been sanitized.
"""

from __future__ import annotations

import os
from pathlib import Path

from config import UPLOAD_DIR  # noqa: E402  (existing config module)

from .interface import StorageInterface


class LocalStorage(StorageInterface):
    def __init__(self) -> None:
        self._root = Path(UPLOAD_DIR)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, filename: str) -> Path:
        return self._root / filename

    def put(self, filename: str, content: bytes, content_type: str) -> str:
        path = self._path(filename)
        with open(path, "wb") as fh:
            fh.write(content)
        return f"/api/uploads/{filename}"

    def get(self, filename: str) -> bytes:
        path = self._path(filename)
        if not path.exists():
            raise FileNotFoundError(filename)
        return path.read_bytes()

    def delete(self, filename: str) -> None:
        path = self._path(filename)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def exists(self, filename: str) -> bool:
        return self._path(filename).exists()
