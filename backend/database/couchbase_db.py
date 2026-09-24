"""
Couchbase adapter for the Database Abstraction Layer.

Shape-compatible with Motor:
    cursor = db.users.find({"role": "admin"}, {"_id": 0}).sort("created_at", -1)
    rows = await cursor.to_list(100)

Storage strategy (Couchbase 7+ best practice):
- ONE native Couchbase collection per logical collection (users, buildings, ...)
- All collections live under scope `_default` of the configured bucket
- Document keys are just the doc's `id` (no prefix; uniqueness is guaranteed per collection)
- N1QL queries target `bucket`.`_default`.`collection` directly (no WHERE type filter)
- GSI indexes are per-collection (no partial-filter predicates needed)

MongoDB operators supported (what the app actually uses):
  Query:  $gt, $gte, $lt, $lte, $in, $ne, $exists, $regex
  Update: $set, $inc, $addToSet (with $each), $unset

Blocking Couchbase SDK calls are dispatched to a thread via asyncio.to_thread
so they do not starve the FastAPI event loop.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.exceptions import (
    CouchbaseException,
    DocumentExistsException,
    DocumentNotFoundException,
)
from couchbase.options import ClusterOptions, QueryOptions, TLSVerifyMode

from .interface import CollectionInterface, CursorInterface, DatabaseInterface


# The scope every collection lives under. See scripts/provision_couchbase_collections.py.
SCOPE_NAME = "_default"


# ---------------------------------------------------------------------------
# Motor-like result objects
# ---------------------------------------------------------------------------

@dataclass
class _InsertOneResult:
    inserted_id: Any


@dataclass
class _InsertManyResult:
    inserted_ids: List[Any]


@dataclass
class _UpdateResult:
    matched_count: int
    modified_count: int
    upserted_id: Any = None


@dataclass
class _DeleteResult:
    deleted_count: int


# ---------------------------------------------------------------------------
# N1QL translation helpers
# ---------------------------------------------------------------------------

class _N1qlBuilder:
    """Translate MongoDB-style filters to N1QL WHERE fragments."""

    def __init__(self):
        self._params: Dict[str, Any] = {}
        self._idx = 0

    def _next_param(self) -> str:
        self._idx += 1
        return f"p{self._idx}"

    def where(self, filter: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        if not filter:
            return "1 = 1", self._params

        conditions = []
        for key, value in filter.items():
            if key == "_id":
                continue  # Couchbase docs don't have Mongo _id
            conditions.append(self._condition(key, value))

        if not conditions:
            return "1 = 1", self._params
        return " AND ".join(conditions), self._params

    def _condition(self, key: str, value: Any) -> str:
        if isinstance(value, dict) and value and all(k.startswith("$") for k in value.keys()):
            # Pre-pass: combine $regex + $options (Mongo-style flags) into a
            # single inline-flag regex that Couchbase RE2 understands.
            if "$regex" in value and "$options" in value:
                pattern = value["$regex"]
                flags = value.pop("$options") or ""
                inline = ""
                if "i" in flags:
                    inline += "i"
                if "s" in flags:
                    inline += "s"
                if "m" in flags:
                    inline += "m"
                if inline and not str(pattern).startswith("(?"):
                    pattern = f"(?{inline}){pattern}"
                value = {**value, "$regex": pattern}

            sub = []
            for op, op_value in value.items():
                p = self._next_param()
                self._params[p] = op_value
                if op == "$in":
                    sub.append(f"`{key}` IN ${p}")
                elif op == "$nin":
                    sub.append(f"`{key}` NOT IN ${p}")
                elif op == "$ne":
                    # Mongo semantics: `$ne` matches docs where the field
                    # is MISSING, NULL, or simply != value. Couchbase's
                    # bare `!= value` excludes MISSING and NULL, which
                    # silently drops legitimate matches (e.g. boolean
                    # flags that were never set). Expand to all three.
                    sub.append(
                        f"(`{key}` IS MISSING OR `{key}` IS NULL OR `{key}` != ${p})"
                    )
                elif op == "$gt":
                    sub.append(f"`{key}` > ${p}")
                elif op == "$gte":
                    sub.append(f"`{key}` >= ${p}")
                elif op == "$lt":
                    sub.append(f"`{key}` < ${p}")
                elif op == "$lte":
                    sub.append(f"`{key}` <= ${p}")
                elif op == "$exists":
                    self._params.pop(p, None)
                    sub.append(
                        f"`{key}` IS NOT MISSING" if op_value else f"`{key}` IS MISSING"
                    )
                elif op == "$regex":
                    # Mongo's $regex does substring matching; Couchbase's
                    # REGEXP_LIKE is anchored. Use REGEXP_CONTAINS for parity.
                    sub.append(f"REGEXP_CONTAINS(`{key}`, ${p})")
                else:
                    raise ValueError(f"Unsupported query operator: {op}")
            return "(" + " AND ".join(sub) + ")"

        p = self._next_param()
        self._params[p] = value
        # MongoDB semantic: when matching a scalar against a field, if the field
        # holds an ARRAY in the document, Mongo treats it as "does the array
        # contain this scalar?". N1QL's `=` does NOT do that, so we OR the two
        # cases. (PPA-70: zone check `{"user_ids": uid}` was silently failing
        # for ALL Couchbase users because user_ids is an array.)
        return f"(`{key}` = ${p} OR ${p} IN `{key}`)"


def _apply_projection(doc: Dict[str, Any], projection: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """MongoDB-style projection: 1=include, 0=exclude. Strips `_id` always."""
    cleaned = {k: v for k, v in doc.items() if k != "_id"}
    if not projection:
        return cleaned

    include_keys = {k for k, v in projection.items() if v == 1}
    exclude_keys = {k for k, v in projection.items() if v == 0}

    real_includes = include_keys - {"_id"}
    if real_includes:
        return {k: v for k, v in cleaned.items() if k in real_includes}
    return {k: v for k, v in cleaned.items() if k not in exclude_keys}


def _apply_update(doc: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Apply MongoDB-style update operators ($set / $inc / $addToSet / $unset) to a copy of the doc."""
    new_doc = dict(doc)

    has_ops = any(k.startswith("$") for k in update.keys())
    if not has_ops:
        new_doc.update(update)
        return new_doc

    for op, payload in update.items():
        if op == "$set":
            for k, v in payload.items():
                new_doc[k] = v
        elif op == "$inc":
            for k, v in payload.items():
                new_doc[k] = (new_doc.get(k) or 0) + v
        elif op == "$addToSet":
            for k, v in payload.items():
                existing = list(new_doc.get(k) or [])
                if isinstance(v, dict) and "$each" in v:
                    for item in v["$each"]:
                        if item not in existing:
                            existing.append(item)
                else:
                    if v not in existing:
                        existing.append(v)
                new_doc[k] = existing
        elif op == "$unset":
            for k in payload.keys():
                new_doc.pop(k, None)
        else:
            raise ValueError(f"Unsupported update operator: {op}")

    return new_doc


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------

class CouchbaseCursor(CursorInterface):
    """Lazy cursor that builds a scoped N1QL query on to_list()."""

    def __init__(
        self,
        cluster: Cluster,
        keyspace_sql: str,           # e.g. "`db_parking`.`_default`.`users`"
        filter: Optional[Dict[str, Any]],
        projection: Optional[Dict[str, Any]],
        collection_alias: str,       # short alias used in SELECT, e.g. "users"
    ):
        self._cluster = cluster
        self._keyspace_sql = keyspace_sql
        self._collection_alias = collection_alias
        self._filter = filter
        self._projection = projection
        self._sort: List[Tuple[str, int]] = []
        self._limit: Optional[int] = None
        self._skip: int = 0

    def sort(self, key_or_list: Any, direction: Optional[int] = None) -> "CouchbaseCursor":
        if isinstance(key_or_list, str):
            self._sort.append((key_or_list, direction if direction is not None else 1))
        elif isinstance(key_or_list, list):
            for entry in key_or_list:
                if isinstance(entry, tuple):
                    field, d = entry
                    self._sort.append((field, d))
                else:
                    self._sort.append((entry, 1))
        return self

    def limit(self, limit: int) -> "CouchbaseCursor":
        self._limit = limit
        return self

    def skip(self, skip: int) -> "CouchbaseCursor":
        self._skip = skip
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        builder = _N1qlBuilder()
        where, params = builder.where(self._filter)

        alias = self._collection_alias
        query = f"SELECT {alias}.* FROM {self._keyspace_sql} AS {alias} WHERE {where}"

        if self._sort:
            order = ", ".join(f"`{f}` {'DESC' if d == -1 else 'ASC'}" for f, d in self._sort)
            query += f" ORDER BY {order}"

        effective_limit = self._limit if self._limit is not None else length
        if effective_limit is not None:
            query += f" LIMIT {int(effective_limit)}"
        if self._skip:
            query += f" OFFSET {int(self._skip)}"

        def _run() -> List[Dict[str, Any]]:
            result = self._cluster.query(query, QueryOptions(named_parameters=params))
            return [_apply_projection(row, self._projection) for row in result]

        return await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

class CouchbaseCollection(CollectionInterface):
    """Wrapper around a real Couchbase collection bound under bucket._default.<name>."""

    def __init__(self, cluster: Cluster, bucket, bucket_name: str, collection_name: str):
        self._cluster = cluster
        self._bucket = bucket
        self._bucket_name = bucket_name
        self._name = collection_name
        # Bind to the actual bucket.scope.collection — no more shared default collection.
        self._kv = bucket.scope(SCOPE_NAME).collection(collection_name)
        # Pre-compute the keyspace for N1QL queries once.
        self._keyspace_sql = (
            f"`{bucket_name}`.`{SCOPE_NAME}`.`{collection_name}`"
        )

    def _key(self, doc_id: Any) -> str:
        # Collection-scoped keyspace => bare id is fine, no prefix needed.
        return str(doc_id)

    async def find_one(
        self,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Tuple[str, int]]] = None,
    ) -> Optional[Dict[str, Any]]:
        # Fast path: direct KV get when filter is just {"id": X} and no sort needed
        if (
            sort is None
            and filter
            and len(filter) == 1
            and "id" in filter
            and not isinstance(filter["id"], dict)
        ):
            def _get() -> Optional[Dict[str, Any]]:
                try:
                    res = self._kv.get(self._key(filter["id"]))
                    return res.content_as[dict]
                except DocumentNotFoundException:
                    return None

            doc = await asyncio.to_thread(_get)
            return _apply_projection(doc, projection) if doc else None

        cursor = self.find(filter, projection)
        if sort:
            cursor.sort(sort)
        cursor.limit(1)
        rows = await cursor.to_list()
        return rows[0] if rows else None

    def find(
        self,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
    ) -> CouchbaseCursor:
        return CouchbaseCursor(
            self._cluster,
            self._keyspace_sql,
            filter,
            projection,
            self._name,
        )

    async def insert_one(self, document: Dict[str, Any]) -> _InsertOneResult:
        doc_id = document.get("id")
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        body = {**document, "id": doc_id}

        def _ins():
            try:
                self._kv.insert(self._key(doc_id), body)
            except DocumentExistsException:
                raise

        await asyncio.to_thread(_ins)
        return _InsertOneResult(inserted_id=doc_id)

    async def insert_many(self, documents: List[Dict[str, Any]]) -> _InsertManyResult:
        ids: List[Any] = []
        for d in documents:
            res = await self.insert_one(d)
            ids.append(res.inserted_id)
        return _InsertManyResult(inserted_ids=ids)

    async def _load_by_filter(
        self, filter: Dict[str, Any], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        cursor = self.find(filter)
        if limit:
            cursor.limit(limit)
        return await cursor.to_list()

    async def update_one(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
    ) -> _UpdateResult:
        # Fast path: filter by id only -> KV get / replace
        if len(filter) == 1 and "id" in filter and not isinstance(filter["id"], dict):
            def _kv_update():
                try:
                    res = self._kv.get(self._key(filter["id"]))
                    current = res.content_as[dict]
                except DocumentNotFoundException:
                    current = None

                if current is None:
                    if not upsert:
                        return _UpdateResult(matched_count=0, modified_count=0)
                    base = {**filter}
                    new_doc = _apply_update(base, update)
                    new_doc.setdefault("id", filter["id"])
                    self._kv.upsert(self._key(filter["id"]), new_doc)
                    return _UpdateResult(matched_count=0, modified_count=0, upserted_id=filter["id"])

                new_doc = _apply_update(current, update)
                self._kv.replace(self._key(filter["id"]), new_doc)
                return _UpdateResult(matched_count=1, modified_count=1)

            return await asyncio.to_thread(_kv_update)

        # General path: N1QL find first match, then KV replace.
        matches = await self._load_by_filter(filter, limit=1)
        if not matches:
            if upsert:
                def _ins_upsert():
                    base = {**filter}
                    new_doc = _apply_update(base, update)
                    doc_id = new_doc.get("id") or base.get("id")
                    if doc_id is None:
                        raise ValueError("Upsert requires 'id' either in filter or update payload")
                    new_doc["id"] = doc_id
                    self._kv.upsert(self._key(doc_id), new_doc)
                    return doc_id

                upserted_id = await asyncio.to_thread(_ins_upsert)
                return _UpdateResult(matched_count=0, modified_count=0, upserted_id=upserted_id)
            return _UpdateResult(matched_count=0, modified_count=0)

        doc = matches[0]
        new_doc = _apply_update(doc, update)

        def _replace():
            self._kv.replace(self._key(doc["id"]), new_doc)

        await asyncio.to_thread(_replace)
        return _UpdateResult(matched_count=1, modified_count=1)

    async def update_many(self, filter: Dict[str, Any], update: Dict[str, Any]) -> _UpdateResult:
        docs = await self._load_by_filter(filter)

        def _bulk_replace():
            count = 0
            for d in docs:
                new_doc = _apply_update(d, update)
                self._kv.replace(self._key(d["id"]), new_doc)
                count += 1
            return count

        n = await asyncio.to_thread(_bulk_replace)
        return _UpdateResult(matched_count=n, modified_count=n)

    async def delete_one(self, filter: Dict[str, Any]) -> _DeleteResult:
        if len(filter) == 1 and "id" in filter and not isinstance(filter["id"], dict):
            def _del():
                try:
                    self._kv.remove(self._key(filter["id"]))
                    return 1
                except DocumentNotFoundException:
                    return 0

            n = await asyncio.to_thread(_del)
            return _DeleteResult(deleted_count=n)

        matches = await self._load_by_filter(filter, limit=1)
        if not matches:
            return _DeleteResult(deleted_count=0)

        def _del_match():
            try:
                self._kv.remove(self._key(matches[0]["id"]))
                return 1
            except DocumentNotFoundException:
                return 0

        n = await asyncio.to_thread(_del_match)
        return _DeleteResult(deleted_count=n)

    async def delete_many(self, filter: Dict[str, Any]) -> _DeleteResult:
        docs = await self._load_by_filter(filter)

        def _bulk_del():
            count = 0
            for d in docs:
                try:
                    self._kv.remove(self._key(d["id"]))
                    count += 1
                except DocumentNotFoundException:
                    pass
            return count

        n = await asyncio.to_thread(_bulk_del)
        return _DeleteResult(deleted_count=n)

    async def count_documents(self, filter: Optional[Dict[str, Any]] = None) -> int:
        builder = _N1qlBuilder()
        where, params = builder.where(filter)
        query = f"SELECT COUNT(*) AS c FROM {self._keyspace_sql} WHERE {where}"

        def _run():
            result = self._cluster.query(query, QueryOptions(named_parameters=params))
            for row in result:
                return int(row.get("c", 0))
            return 0

        return await asyncio.to_thread(_run)

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # App doesn't call aggregate() anywhere today. Placeholder returns [].
        return []

    async def find_one_and_update(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        return_document: bool = False,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Mongo-shaped find_one_and_update for Couchbase.

        Implementation: locate the doc (KV fast-path if filter is just {"id": X},
        else N1QL), apply the update operators, KV.replace the doc, then return
        the BEFORE or AFTER snapshot per `return_document`.
        """
        # Helper: handle Motor's pymongo.ReturnDocument enum values too
        return_after = bool(return_document)

        # Fast path: id-only filter -> single KV round-trip + replace
        if len(filter) == 1 and "id" in filter and not isinstance(filter["id"], dict):
            def _kv_op() -> Optional[Dict[str, Any]]:
                try:
                    res = self._kv.get(self._key(filter["id"]))
                    before = res.content_as[dict]
                except DocumentNotFoundException:
                    if not upsert:
                        return None
                    base = {**filter}
                    new_doc = _apply_update(base, update)
                    new_doc.setdefault("id", filter["id"])
                    self._kv.upsert(self._key(filter["id"]), new_doc)
                    return new_doc if return_after else None

                after = _apply_update(before, update)
                self._kv.replace(self._key(filter["id"]), after)
                return after if return_after else before

            doc = await asyncio.to_thread(_kv_op)
            return _apply_projection(doc, projection) if doc else None

        # General path
        matches = await self._load_by_filter(filter, limit=1)
        if not matches:
            if not upsert:
                return None
            def _ins_upsert():
                base = {**filter}
                new_doc = _apply_update(base, update)
                doc_id = new_doc.get("id") or base.get("id")
                if doc_id is None:
                    raise ValueError("Upsert requires 'id' in filter or update payload")
                new_doc["id"] = doc_id
                self._kv.upsert(self._key(doc_id), new_doc)
                return new_doc
            after = await asyncio.to_thread(_ins_upsert)
            return _apply_projection(after, projection) if return_after else None

        before = matches[0]
        after = _apply_update(before, update)

        def _replace():
            self._kv.replace(self._key(before["id"]), after)
        await asyncio.to_thread(_replace)

        return _apply_projection(after if return_after else before, projection)

    async def find_one_and_delete(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mongo-shaped find_one_and_delete: returns the doc that was removed."""
        if len(filter) == 1 and "id" in filter and not isinstance(filter["id"], dict):
            def _kv_op():
                try:
                    res = self._kv.get(self._key(filter["id"]))
                    doc = res.content_as[dict]
                except DocumentNotFoundException:
                    return None
                try:
                    self._kv.remove(self._key(filter["id"]))
                except DocumentNotFoundException:
                    pass
                return doc

            doc = await asyncio.to_thread(_kv_op)
            return _apply_projection(doc, projection) if doc else None

        matches = await self._load_by_filter(filter, limit=1)
        if not matches:
            return None
        doc = matches[0]
        def _remove():
            try:
                self._kv.remove(self._key(doc["id"]))
            except DocumentNotFoundException:
                pass
        await asyncio.to_thread(_remove)
        return _apply_projection(doc, projection)

    async def create_index(self, keys: Any, **kwargs: Any) -> Any:
        # Centralized in CouchbaseDatabase.create_indexes(); per-call no-op.
        return None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class CouchbaseDatabase(DatabaseInterface):
    def __init__(
        self,
        connection_string: str,
        bucket_name: str,
        username: str,
        password: str,
        *,
        deployment: str = "capella",
        trust_store_path: Optional[str] = None,
        cert_path: Optional[str] = None,
        tls_verify: str = "peer",
    ):
        """Couchbase adapter — works against both Capella and Enterprise.

        Args:
            connection_string: ``couchbases://...`` (TLS) or ``couchbase://...``.
            bucket_name, username, password: cluster credentials.
            deployment: ``"capella"`` (default, applies the SDK
                ``wan_development`` profile for cloud latency) or
                ``"enterprise"`` (LAN; profile NOT applied).
            trust_store_path: PEM file with the Enterprise cluster's CA cert.
                Required when ``couchbases://`` points at a cluster whose
                cert chains to an internal/private CA (typical for on-prem).
            cert_path: PEM client cert for mutual-TLS. Rarely used; only set
                if your Enterprise cluster requires client-auth.
            tls_verify: ``"peer"`` (default, full chain validation) or
                ``"none"`` (emergency: skip TLS verification — DEV ONLY).
        """
        self._conn = connection_string
        self._bucket_name = bucket_name
        self._username = username
        self._password = password
        self._deployment = (deployment or "capella").strip().lower()
        self._trust_store_path = trust_store_path or None
        self._cert_path = cert_path or None
        self._tls_verify = (tls_verify or "peer").strip().lower()
        self._cluster: Optional[Cluster] = None
        self._bucket = None
        self._collections: Dict[str, CouchbaseCollection] = {}

    async def connect(self) -> None:
        def _blocking_connect():
            auth = PasswordAuthenticator(self._username, self._password)

            # Build kwargs only for fields the operator actually set so we
            # don't pass empty paths to the SDK (would fail validation).
            opt_kwargs: Dict[str, Any] = {}
            if self._trust_store_path:
                opt_kwargs["trust_store_path"] = self._trust_store_path
            if self._cert_path:
                opt_kwargs["cert_path"] = self._cert_path
            if self._tls_verify == "none":
                opt_kwargs["tls_verify"] = TLSVerifyMode.NONE

            options = ClusterOptions(auth, **opt_kwargs)

            # wan_development tunes timeouts for high-latency Capella links;
            # on a LAN-attached Enterprise cluster it just slows things down.
            if self._deployment == "capella":
                try:
                    options.apply_profile("wan_development")
                except Exception:
                    pass

            cluster = Cluster(self._conn, options)
            cluster.wait_until_ready(timedelta(seconds=30))
            bucket = cluster.bucket(self._bucket_name)
            # Touch the default scope to warm up the bucket connection.
            _ = bucket.scope(SCOPE_NAME)
            return cluster, bucket

        self._cluster, self._bucket = await asyncio.to_thread(_blocking_connect)

    async def disconnect(self) -> None:
        self._cluster = None
        self._bucket = None
        self._collections = {}

    def get_collection(self, name: str) -> CouchbaseCollection:
        if self._cluster is None or self._bucket is None:
            raise RuntimeError("Couchbase not connected; call connect() first")
        if name not in self._collections:
            self._collections[name] = CouchbaseCollection(
                self._cluster, self._bucket, self._bucket_name, name
            )
        return self._collections[name]

    def __getattr__(self, name: str) -> CouchbaseCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        if "_cluster" not in self.__dict__:
            raise AttributeError(name)
        return self.get_collection(name)

    @property
    def is_connected(self) -> bool:
        return self._cluster is not None and self._bucket is not None

    async def create_indexes(self) -> None:
        """Create collection-scoped GSI indexes (no `WHERE type=` partial filters needed)."""
        if self._cluster is None:
            raise RuntimeError("Couchbase not connected")

        b = self._bucket_name
        s = SCOPE_NAME
        # Each collection gets a primary index (for ad-hoc queries) plus hot-path indexes.
        # All statements are idempotent (IF NOT EXISTS).
        base_statements = [
            # Every collection needs a primary index so N1QL can run without a pre-built one
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`users`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`sessions`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`buildings`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`floors`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`parking_slots`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`vehicles`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`zones`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`parking_configs`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`building_policies`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`slot_registrations`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`reservations`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`waitlist_entries`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`event_blocks`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`notifications`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`site_content`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`templates`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`ai_insights`",
            f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{b}`.`{s}`.`migrations`",
            # Hot-path secondary indexes on fields we query by
            f"CREATE INDEX IF NOT EXISTS `idx_users_email` ON `{b}`.`{s}`.`users`(`email`)",
            f"CREATE INDEX IF NOT EXISTS `idx_users_role` ON `{b}`.`{s}`.`users`(`role`)",
            f"CREATE INDEX IF NOT EXISTS `idx_sessions_user` ON `{b}`.`{s}`.`sessions`(`user_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_res_user` ON `{b}`.`{s}`.`reservations`(`user_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_res_building` ON `{b}`.`{s}`.`reservations`(`building_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_res_slot_date` ON `{b}`.`{s}`.`reservations`(`slot_id`, `date`)",
            f"CREATE INDEX IF NOT EXISTS `idx_res_qr` ON `{b}`.`{s}`.`reservations`(`qr_token`)",
            f"CREATE INDEX IF NOT EXISTS `idx_floors_bldg` ON `{b}`.`{s}`.`floors`(`building_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_slots_floor` ON `{b}`.`{s}`.`parking_slots`(`floor_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_vehicles_user` ON `{b}`.`{s}`.`vehicles`(`user_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_notif_user_created` ON `{b}`.`{s}`.`notifications`(`user_id`, `created_at`)",
            f"CREATE INDEX IF NOT EXISTS `idx_wl_bldg_date_status` ON `{b}`.`{s}`.`waitlist_entries`(`building_id`, `preferred_date`, `status`)",
            f"CREATE INDEX IF NOT EXISTS `idx_wl_user_status` ON `{b}`.`{s}`.`waitlist_entries`(`user_id`, `status`)",
            f"CREATE INDEX IF NOT EXISTS `idx_bp_bldg` ON `{b}`.`{s}`.`building_policies`(`building_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_pc_bldg` ON `{b}`.`{s}`.`parking_configs`(`building_id`)",
            f"CREATE INDEX IF NOT EXISTS `idx_sc_key` ON `{b}`.`{s}`.`site_content`(`key`)",
            f"CREATE INDEX IF NOT EXISTS `idx_sr_slot_status` ON `{b}`.`{s}`.`slot_registrations`(`slot_id`, `status`)",
            f"CREATE INDEX IF NOT EXISTS `idx_sr_user_status` ON `{b}`.`{s}`.`slot_registrations`(`user_id`, `status`)",
            f"CREATE INDEX IF NOT EXISTS `idx_sr_bldg_status` ON `{b}`.`{s}`.`slot_registrations`(`building_id`, `status`)",
            f"CREATE INDEX IF NOT EXISTS `idx_eb_bldg_date` ON `{b}`.`{s}`.`event_blocks`(`building_id`, `date`)",
        ]

        def _run_one(stmt: str):
            try:
                self._cluster.query(stmt).execute()
            except CouchbaseException as e:
                if "already exists" not in str(e).lower():
                    print(f"[Couchbase] index warn: {e}")

        # Parallel execution keeps startup under a few seconds even on Capella WAN.
        await asyncio.gather(*[asyncio.to_thread(_run_one, s) for s in base_statements])
