"""
MarketTrust AI — MinIO Object Storage Client with Local Fallback.

Provides upload, download, and URL generation for investigation media files.
Falls back to local disk storage if MinIO service is unavailable.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level state
_client = None
_use_local_storage = False
_local_storage_dir = Path("uploads_data")


def init_storage() -> None:
    """Initialize MinIO client or fall back to local disk storage."""
    global _client, _use_local_storage
    try:
        from minio import Minio

        _client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        bucket = settings.minio_bucket
        if not _client.bucket_exists(bucket):
            _client.make_bucket(bucket)
            logger.info(f"Created MinIO bucket: {bucket}")
        else:
            logger.info(f"MinIO bucket exists: {bucket}")
        _use_local_storage = False
    except Exception as e:
        logger.warning(
            f"MinIO unavailable ({e}). Falling back to local disk storage in {_local_storage_dir}"
        )
        _use_local_storage = True
        _local_storage_dir.mkdir(parents=True, exist_ok=True)


def upload_file(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload raw bytes to MinIO or local storage."""
    if _use_local_storage or _client is None:
        file_path = _local_storage_dir / object_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        logger.info(f"Saved locally: {object_name} ({len(data)} bytes)")
        return object_name

    stream = io.BytesIO(data)
    _client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        data=stream,
        length=len(data),
        content_type=content_type,
    )
    logger.info(f"Uploaded to MinIO: {object_name} ({len(data)} bytes)")
    return object_name


def download_file(object_name: str) -> bytes:
    """Download a file from MinIO or local storage as bytes."""
    if _use_local_storage or _client is None:
        file_path = _local_storage_dir / object_name
        if not file_path.exists():
            raise FileNotFoundError(f"Local file not found: {object_name}")
        return file_path.read_bytes()

    response = _client.get_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
    )
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(
    object_name: str,
    expires_seconds: int = 3600,
) -> str:
    """Generate a URL for temporary access to an object."""
    if _use_local_storage or _client is None:
        return f"/api/uploads/{object_name}"

    from datetime import timedelta

    return _client.presigned_get_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        expires=timedelta(seconds=expires_seconds),
    )


def delete_file(object_name: str) -> None:
    """Delete an object from MinIO or local storage."""
    if _use_local_storage or _client is None:
        file_path = _local_storage_dir / object_name
        file_path.unlink(missing_ok=True)
        logger.info(f"Deleted local file: {object_name}")
        return

    _client.remove_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
    )
    logger.info(f"Deleted MinIO object: {object_name}")
