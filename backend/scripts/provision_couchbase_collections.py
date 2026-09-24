"""
Provision the Couchbase Capella bucket schema:
- Scope: _default (already exists on every bucket)
- Collections: 18 real Couchbase collections matching MongoDB collection names

Run once before migrating data. Safe to re-run (idempotent).

Usage:
    cd /app/backend && python scripts/provision_couchbase_collections.py
"""

import os
import sys
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.management.collections import CollectionSpec
from couchbase.options import ClusterOptions
from couchbase.exceptions import CollectionAlreadyExistsException, CouchbaseException

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

COLLECTIONS = [
    "users",
    "sessions",
    "buildings",
    "floors",
    "parking_slots",
    "vehicles",
    "zones",
    "parking_configs",
    "building_policies",
    "slot_registrations",
    "reservations",
    "waitlist_entries",
    "event_blocks",
    "notifications",
    "site_content",
    "templates",
    "ai_insights",
    "migrations",
]

SCOPE_NAME = "_default"


def main():
    auth = PasswordAuthenticator(
        os.environ["COUCHBASE_USERNAME"], os.environ["COUCHBASE_PASSWORD"]
    )
    options = ClusterOptions(auth)
    try:
        options.apply_profile("wan_development")
    except Exception:
        pass

    cluster = Cluster(os.environ["COUCHBASE_CONNECTION_STRING"], options)
    cluster.wait_until_ready(timedelta(seconds=30))

    bucket_name = os.environ["COUCHBASE_BUCKET"]
    bucket = cluster.bucket(bucket_name)
    coll_mgr = bucket.collections()

    created, existing, errors = [], [], []
    for name in COLLECTIONS:
        try:
            # Prefer the new 4.2+ signature: create_collection(scope_name, collection_name)
            coll_mgr.create_collection(SCOPE_NAME, name)
            created.append(name)
            print(f"  + created  {SCOPE_NAME}.{name}")
        except CollectionAlreadyExistsException:
            existing.append(name)
            print(f"  = exists   {SCOPE_NAME}.{name}")
        except CouchbaseException as e:
            if "already exist" in str(e).lower():
                existing.append(name)
                print(f"  = exists   {SCOPE_NAME}.{name}")
            else:
                errors.append((name, str(e)))
                print(f"  ! ERROR    {SCOPE_NAME}.{name}: {e}")

    print("-" * 60)
    print(f"Created: {len(created)}  Existing: {len(existing)}  Errors: {len(errors)}")
    if errors:
        print("\nFAILED collections:")
        for name, err in errors:
            print(f"  {name}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
