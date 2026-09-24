"""
MongoDB adapter for the Database Abstraction Layer.

This is a passthrough wrapper around Motor. We expose the raw Motor database
via attribute access so that `db.users.find(...)` etc. continues to work
exactly as before — zero behavior change in MongoDB mode.
"""

from typing import Any, Dict, List, Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorCursor,
    AsyncIOMotorDatabase,
)

from .interface import CollectionInterface, CursorInterface, DatabaseInterface


class MongoDBDatabase(DatabaseInterface):
    """Thin wrapper that delegates to Motor via attribute access."""

    def __init__(self, connection_string: str, database_name: str):
        self._connection_string = connection_string
        self._database_name = database_name
        # Motor is lazy: instantiating the client does not perform network I/O,
        # so we connect eagerly to preserve the previous module-import behavior
        # where `from database import db` yields an immediately-usable handle.
        self._client: Optional[AsyncIOMotorClient] = AsyncIOMotorClient(
            connection_string,
            maxPoolSize=50,
            minPoolSize=5,
            maxIdleTimeMS=30000,
        )
        self._db: Optional[AsyncIOMotorDatabase] = self._client[database_name]

    async def connect(self) -> None:
        # Idempotent: the client was created in __init__. Reconnect if it was closed.
        if self._client is None:
            self._client = AsyncIOMotorClient(
                self._connection_string,
                maxPoolSize=50,
                minPoolSize=5,
                maxIdleTimeMS=30000,
            )
            self._db = self._client[self._database_name]

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._db = None

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        if self._db is None:
            raise RuntimeError("MongoDB not connected; call connect() first")
        return self._db[name]

    def __getattr__(self, name: str) -> Any:
        # Motor's AsyncIOMotorDatabase already exposes collections via attribute access
        # and supports db.command() etc. Delegate everything to it.
        if name.startswith("_"):
            raise AttributeError(name)
        db = self.__dict__.get("_db")
        if db is None:
            raise RuntimeError("MongoDB not connected; call connect() first")
        return getattr(db, name)

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._db is not None

    @property
    def client(self) -> Optional[AsyncIOMotorClient]:
        return self._client

    @property
    def raw_db(self) -> Optional[AsyncIOMotorDatabase]:
        return self._db

    async def create_indexes(self) -> None:
        """Ensure all MongoDB indexes exist. Safe to call repeatedly."""
        if self._db is None:
            raise RuntimeError("MongoDB not connected")
        db = self._db
        await db.users.create_index("id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.sessions.create_index("id", unique=True)
        await db.sessions.create_index("user_id")
        await db.reservations.create_index("id", unique=True)
        await db.reservations.create_index("user_id")
        await db.reservations.create_index("building_id")
        await db.reservations.create_index([("slot_id", 1), ("date", 1), ("status", 1)])
        await db.reservations.create_index("qr_token")
        await db.buildings.create_index("id", unique=True)
        await db.floors.create_index("id", unique=True)
        await db.floors.create_index("building_id")
        await db.parking_slots.create_index("id", unique=True)
        await db.parking_slots.create_index("floor_id")
        await db.vehicles.create_index("id", unique=True)
        await db.vehicles.create_index("user_id")
        await db.zones.create_index("id", unique=True)
        await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
        await db.parking_configs.create_index("building_id", unique=True)
        await db.ai_insights.create_index("generated_at")
        await db.site_content.create_index("key", unique=True)
        await db.building_policies.create_index("building_id", unique=True)
        await db.slot_registrations.create_index("id", unique=True)
        await db.slot_registrations.create_index([("slot_id", 1), ("status", 1)])
        await db.slot_registrations.create_index([("user_id", 1), ("status", 1)])
        await db.slot_registrations.create_index([("building_id", 1), ("status", 1)])
        await db.waitlist_entries.create_index("id", unique=True)
        await db.waitlist_entries.create_index([("building_id", 1), ("preferred_date", 1), ("status", 1)])
        await db.waitlist_entries.create_index([("user_id", 1), ("status", 1)])
