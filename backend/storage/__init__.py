"""Storage abstraction so the backend can persist uploads either on local
disk (dev / docker-compose) or in S3-compatible object storage (Huawei OBS
on CCE production).

Selection
---------
Set ``STORAGE_TYPE`` env var:
  * ``local``  (default) — writes under ``UPLOAD_DIR`` on the container
                            filesystem. Original behaviour.
  * ``obs``                — writes to a Huawei OBS bucket via the S3-compatible
                            API. Required when running on Huawei CCE because
                            pods are stateless and there is no shared volume.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .interface import StorageInterface

log = logging.getLogger(__name__)

_storage: Optional[StorageInterface] = None


def get_storage() -> StorageInterface:
    """Lazy singleton — instantiated on first call so tests can override env."""
    global _storage
    if _storage is None:
        _storage = _build_storage()
    return _storage


def _build_storage() -> StorageInterface:
    backend = os.environ.get("STORAGE_TYPE", "local").strip().lower()
    if backend == "obs":
        from .obs import OBSStorage

        log.info("storage backend: obs (bucket=%s)", os.environ.get("OBS_BUCKET", "?"))
        return OBSStorage(
            endpoint=os.environ["OBS_ENDPOINT"],
            bucket=os.environ["OBS_BUCKET"],
            access_key=os.environ["OBS_ACCESS_KEY"],
            secret_key=os.environ["OBS_SECRET_KEY"],
            region=os.environ.get("OBS_REGION", "default"),
            prefix=os.environ.get("OBS_KEY_PREFIX", "uploads/"),
        )

    from .local import LocalStorage

    log.info("storage backend: local")
    return LocalStorage()


def reset_storage_for_tests() -> None:
    """Internal: drop the cached instance so tests can re-init with new env."""
    global _storage
    _storage = None
