"""Minimal storage interface — kept tiny on purpose. The two operations the
app actually performs against uploaded files are write and read; delete is
provided for completeness (used by the floor-layout cleanup path).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageInterface(ABC):
    @abstractmethod
    def put(self, filename: str, content: bytes, content_type: str) -> str:
        """Persist ``content`` under ``filename``. Returns the relative URL the
        frontend should use to fetch it back (always ``/api/uploads/{filename}``
        — the GET endpoint then routes through this same interface)."""

    @abstractmethod
    def get(self, filename: str) -> bytes:
        """Return the bytes. Raises FileNotFoundError if missing."""

    @abstractmethod
    def delete(self, filename: str) -> None:
        """Best-effort delete. Silent if the object doesn't exist."""

    @abstractmethod
    def exists(self, filename: str) -> bool: ...
