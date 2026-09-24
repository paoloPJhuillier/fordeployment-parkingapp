"""Huawei OBS storage backend — talks to OBS via its S3-compatible API using
boto3 (already in requirements.txt for other reasons).

Why boto3 and not Huawei's `obs` SDK?
  * boto3 is mature, well-documented, and already installed.
  * OBS implements the S3 API faithfully enough for `put_object` / `get_object`
    / `delete_object` / `head_object` — the four operations we need.
  * If the customer's compliance team requires the official Huawei SDK we can
    drop in a sibling backend later; the StorageInterface keeps it isolated.

Required env vars (see backend/storage/__init__.py for the wiring):
  OBS_ENDPOINT      e.g. https://obs.your-region.your-hcs.local
  OBS_BUCKET        the bucket the app writes to (must already exist)
  OBS_ACCESS_KEY    AK
  OBS_SECRET_KEY    SK
  OBS_REGION        OBS regions don't matter for SigV4 in HCS; "default" is fine
  OBS_KEY_PREFIX    optional, defaults to "uploads/"  — keeps app objects
                    namespaced inside the bucket.
"""

from __future__ import annotations

import logging
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .interface import StorageInterface

log = logging.getLogger(__name__)


class OBSStorage(StorageInterface):
    def __init__(
        self,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "default",
        prefix: str = "uploads/",
    ) -> None:
        self._bucket = bucket
        # Path-style addressing is required for most S3-compatible clouds
        # because the bucket is not on a unique DNS hostname.
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""

    def _key(self, filename: str) -> str:
        return f"{self._prefix}{filename}"

    def put(self, filename: str, content: bytes, content_type: str) -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=self._key(filename),
            Body=content,
            ContentType=content_type,
        )
        return f"/api/uploads/{filename}"

    def get(self, filename: str) -> bytes:
        try:
            res = self._client.get_object(Bucket=self._bucket, Key=self._key(filename))
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                raise FileNotFoundError(filename) from e
            raise
        return res["Body"].read()

    def delete(self, filename: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=self._key(filename))
        except ClientError as e:
            log.warning("OBS delete failed for %s: %s", filename, e)

    def exists(self, filename: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._key(filename))
            return True
        except ClientError:
            return False

    # Optional: presigned URL — not used today (we proxy through the backend
    # to keep auth checks centralised) but useful if the customer ever wants
    # to offload large image traffic from the API tier.
    def presigned_url(self, filename: str, expires: int = 600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": self._key(filename)},
            ExpiresIn=expires,
        )
