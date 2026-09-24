"""
Env-based Couchbase connectivity check (no hardcoded credentials).

Reads COUCHBASE_* from backend/.env and verifies:
  1. Authentication + cluster readiness
  2. Bucket open
  3. KV upsert -> get -> remove round trip on the _default collection
  4. A N1QL COUNT(*) query

Exits non-zero on the first failing step.

Usage:
    cd backend && python scripts/check_couchbase_env.py
"""
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions, TLSVerifyMode
from couchbase.exceptions import CouchbaseException

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def main() -> None:
    conn = os.environ["COUCHBASE_CONNECTION_STRING"]
    bucket_name = os.environ["COUCHBASE_BUCKET"]
    username = os.environ["COUCHBASE_USERNAME"]
    password = os.environ["COUCHBASE_PASSWORD"]
    deployment = os.environ.get("COUCHBASE_DEPLOYMENT", "capella").strip().lower()
    trust_store = os.environ.get("COUCHBASE_TRUST_STORE_PATH") or None
    cert_path = os.environ.get("COUCHBASE_CERT_PATH") or None
    tls_verify = os.environ.get("COUCHBASE_TLS_VERIFY", "peer").strip().lower()

    print(f"[1/4] Authenticating to {conn} (deployment={deployment}) ...")
    auth = PasswordAuthenticator(username, password)
    opt_kwargs = {}
    if trust_store:
        opt_kwargs["trust_store_path"] = trust_store
    if cert_path:
        opt_kwargs["cert_path"] = cert_path
    if tls_verify == "none":
        opt_kwargs["tls_verify"] = TLSVerifyMode.NONE
    options = ClusterOptions(auth, **opt_kwargs)
    if deployment == "capella":
        try:
            options.apply_profile("wan_development")
        except Exception:
            pass

    try:
        cluster = Cluster(conn, options)
        cluster.wait_until_ready(timedelta(seconds=30))
    except CouchbaseException as e:
        print(f"FAIL: cluster connection: {e}")
        sys.exit(1)
    print("      connected.")

    print(f"[2/4] Opening bucket '{bucket_name}' ...")
    try:
        bucket = cluster.bucket(bucket_name)
        collection = bucket.default_collection()
    except CouchbaseException as e:
        print(f"FAIL: bucket access: {e}")
        sys.exit(1)
    print("      bucket opened.")

    print("[3/4] KV upsert -> get -> remove round trip ...")
    key = f"__healthcheck::{int(time.time())}"
    doc = {"msg": "env-based healthcheck", "ts": time.time()}
    try:
        collection.upsert(key, doc)
        got = collection.get(key).content_as[dict]
        assert got.get("msg") == doc["msg"], "payload mismatch"
        collection.remove(key)
    except (CouchbaseException, AssertionError) as e:
        print(f"FAIL: KV round trip: {e}")
        sys.exit(1)
    print(f"      OK (key={key}).")

    print("[4/4] N1QL COUNT(*) ...")
    try:
        cluster.query(f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{bucket_name}`").execute()
        result = cluster.query(f"SELECT COUNT(*) AS c FROM `{bucket_name}`")
        count = 0
        for row in result:
            count = row.get("c", 0)
        print(f"      N1QL OK. Bucket document count: {count}")
    except CouchbaseException as e:
        print(f"FAIL: N1QL: {e}")
        sys.exit(1)

    print("\nSUCCESS: Couchbase is reachable and functional.")


if __name__ == "__main__":
    main()
