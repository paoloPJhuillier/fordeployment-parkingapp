"""
Standalone script to verify Couchbase Capella connectivity.
Usage: cd /app/backend && python scripts/test_couchbase_connection.py
"""
import sys
import time
from datetime import timedelta

from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
from couchbase.auth import PasswordAuthenticator
from couchbase.exceptions import CouchbaseException

CONNECTION_STRING = "couchbases://cb.e6bams0qd8ow9578.cloud.couchbase.com"
BUCKET_NAME = "db_parking"
USERNAME = "parking_app"
PASSWORD = "Ce%lDtOtI-G4"


def main():
    print("[1/5] Authenticating...")
    auth = PasswordAuthenticator(USERNAME, PASSWORD)
    options = ClusterOptions(auth)
    # Capella requires TLS; default profile forces wan_development for latency tolerance
    try:
        options.apply_profile("wan_development")
    except Exception:
        pass

    print(f"[2/5] Connecting to {CONNECTION_STRING} ...")
    try:
        cluster = Cluster(CONNECTION_STRING, options)
        cluster.wait_until_ready(timedelta(seconds=30))
    except CouchbaseException as e:
        print(f"FAIL: cluster connection: {e}")
        sys.exit(1)
    print("Connected to cluster.")

    print(f"[3/5] Opening bucket '{BUCKET_NAME}'...")
    try:
        bucket = cluster.bucket(BUCKET_NAME)
        collection = bucket.default_collection()
    except CouchbaseException as e:
        print(f"FAIL: bucket access: {e}")
        sys.exit(1)
    print("Bucket opened.")

    print("[4/5] KV upsert + get round-trip...")
    key = f"__healthcheck::{int(time.time())}"
    doc = {"type": "healthcheck", "msg": "hello from abstraction layer", "ts": time.time()}
    try:
        collection.upsert(key, doc)
        got = collection.get(key)
        got_doc = got.content_as[dict]
        assert got_doc.get("msg") == doc["msg"], "payload mismatch"
        collection.remove(key)
    except CouchbaseException as e:
        print(f"FAIL: KV round-trip: {e}")
        sys.exit(1)
    print(f"KV round-trip OK (key={key}).")

    print("[5/5] Ensuring primary index and running N1QL SELECT...")
    try:
        cluster.query(f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{BUCKET_NAME}`").execute()
    except CouchbaseException as e:
        # Non-fatal; index may exist or require scope-aware syntax
        print(f"WARN: primary index: {e}")

    try:
        result = cluster.query(f"SELECT COUNT(*) AS c FROM `{BUCKET_NAME}`")
        count = 0
        for row in result:
            count = row.get("c", 0)
        print(f"N1QL OK. Bucket document count: {count}")
    except CouchbaseException as e:
        print(f"FAIL: N1QL: {e}")
        sys.exit(1)

    print("\nSUCCESS: Couchbase Capella is reachable and functional.")


if __name__ == "__main__":
    main()
