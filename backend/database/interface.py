"""
Database Interface - Abstract base classes for database operations.

The API is shape-compatible with Motor (async MongoDB driver):
    cursor = db.collection_name.find(filter, projection)   # sync, returns cursor
    results = await cursor.to_list(length)                 # async

This allows MongoDB and Couchbase adapters to be interchangeable behind the
same call-sites used throughout the application.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CursorInterface(ABC):
    """Motor-shaped cursor; supports chainable sort/limit/skip and async to_list."""

    @abstractmethod
    def sort(self, key_or_list: Any, direction: Optional[int] = None) -> "CursorInterface":
        ...

    @abstractmethod
    def limit(self, limit: int) -> "CursorInterface":
        ...

    @abstractmethod
    def skip(self, skip: int) -> "CursorInterface":
        ...

    @abstractmethod
    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        ...


class CollectionInterface(ABC):
    """Motor-shaped collection/bucket operations."""

    @abstractmethod
    async def find_one(
        self,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def find(
        self,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
    ) -> CursorInterface:
        """Sync call that returns a cursor; matches Motor's API."""
        ...

    @abstractmethod
    async def insert_one(self, document: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def insert_many(self, documents: List[Dict[str, Any]]) -> Any:
        ...

    @abstractmethod
    async def update_one(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
    ) -> Any:
        ...

    @abstractmethod
    async def update_many(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
    ) -> Any:
        ...

    @abstractmethod
    async def delete_one(self, filter: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def delete_many(self, filter: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def count_documents(self, filter: Optional[Dict[str, Any]] = None) -> int:
        ...

    @abstractmethod
    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def find_one_and_update(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        return_document: bool = False,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Motor-style find_one_and_update.

        return_document=True (or pymongo's ReturnDocument.AFTER) returns the
        updated doc. Default returns the original (pre-update) doc.
        """
        ...

    @abstractmethod
    async def find_one_and_delete(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def create_index(self, keys: Any, **kwargs: Any) -> Any:
        """No-op friendly; adapters translate to their native index syntax where possible."""
        ...


class DatabaseInterface(ABC):
    """Motor-shaped database with attribute-access collections (e.g., db.users)."""

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    def get_collection(self, name: str) -> CollectionInterface:
        ...

    def __getattr__(self, name: str) -> CollectionInterface:  # pragma: no cover
        # Subclasses should set common attrs before this fallback fires.
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get_collection(name)

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        ...
