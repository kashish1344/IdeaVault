"""
MinIO (S3-compatible) storage service.
Uploads generated media and returns a public URL.
"""

from __future__ import annotations

import io
import logging
import os
import uuid
from urllib.request import urlopen

from minio import Minio
from minio.error import S3Error

from ..core.config import get_settings

logger = logging.getLogger("ideavault.storage")
settings = get_settings()


class StorageService:

    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
                self._client.set_bucket_policy(
                    self._bucket,
                    _public_read_policy(self._bucket),
                )
        except S3Error as exc:
            logger.error("bucket init failed: %s", exc)

    async def upload_from_url(
        self, source_url: str, media_type: str, job_id: str
    ) -> str:
        """Download from source_url and re-upload to MinIO. Returns public URL."""
        import asyncio
        loop = asyncio.get_event_loop()

        ext = "mp4" if media_type == "video" else "png"
        object_name = f"{media_type}s/{job_id}.{ext}"

        try:
            data = await loop.run_in_executor(
                None, lambda: urlopen(source_url, timeout=60).read()
            )
            content_type = "video/mp4" if media_type == "video" else "image/png"
            await loop.run_in_executor(
                None,
                lambda: self._client.put_object(
                    self._bucket,
                    object_name,
                    io.BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                ),
            )
            return self._public_url(object_name)
        except Exception as exc:
            logger.exception("upload failed for job %s: %s", job_id, exc)
            return source_url  # fall back to original URL

    def _public_url(self, object_name: str) -> str:
        scheme = "https" if settings.minio_secure else "http"
        return f"{scheme}://{settings.minio_endpoint}/{self._bucket}/{object_name}"


def _public_read_policy(bucket: str) -> str:
    import json
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket}/*"],
        }],
    })
