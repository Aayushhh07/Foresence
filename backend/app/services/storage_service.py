"""
Cloudflare R2 storage service.
Uses boto3 with S3-compatible API to upload images and return public URLs.
"""
import logging
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

import os
from pathlib import Path

logger = logging.getLogger(__name__)

_s3_client = None

# Local static directory fallback path (backend/static)
STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


def _is_r2_enabled() -> bool:
    """Check if Cloudflare R2 credentials are set and not default placeholders."""
    key = settings.cloudflare_r2_access_key.strip()
    secret = settings.cloudflare_r2_secret_key.strip()
    endpoint = settings.cloudflare_r2_endpoint.strip()

    if not key or not secret or not endpoint:
        return False
    if any(placeholder in key.lower() for placeholder in ("demo", "your_r2")):
        return False
    return True


def _get_s3_client():
    """Get or create the boto3 S3 client configured for Cloudflare R2."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.cloudflare_r2_endpoint,
            aws_access_key_id=settings.cloudflare_r2_access_key,
            aws_secret_access_key=settings.cloudflare_r2_secret_key,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
            region_name="auto",
        )
    return _s3_client


async def upload_bytes_to_r2(
    data: bytes,
    key: str,
    content_type: str = "image/png",
) -> str:
    """
    Upload bytes to Cloudflare R2 and return the public URL.
    Falls back to storing local static files if R2 is not enabled.
    Key should be a path like 'ndvi/zone_id/scan_id.png'.
    """
    if not _is_r2_enabled():
        try:
            dest_path = STATIC_DIR / key
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(data)

            # Construct backend URL serving static files (e.g. replace frontend port 5173 with backend port 8000)
            backend_base_url = settings.frontend_url.replace(":5173", ":8000")
            public_url = f"{backend_base_url.rstrip('/')}/static/{key}"
            logger.info(f"Saved locally (R2 fallback): {key} ({len(data)} bytes) -> {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Local storage write failed for key '{key}': {e}", exc_info=True)
            raise

    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.cloudflare_r2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=86400",
        )
        public_url = f"{settings.cloudflare_r2_public_url.rstrip('/')}/{key}"
        logger.info(f"Uploaded to R2: {key} ({len(data)} bytes)")
        return public_url

    except ClientError as e:
        logger.error(f"R2 upload failed for key '{key}': {e}", exc_info=True)
        raise


async def delete_from_r2(key: str) -> None:
    """Delete an object from R2 or local storage."""
    if not _is_r2_enabled():
        try:
            dest_path = STATIC_DIR / key
            if dest_path.exists():
                dest_path.unlink()
                logger.info(f"Deleted locally: {key}")
        except Exception as e:
            logger.error(f"Local delete failed for key '{key}': {e}")
        return

    try:
        client = _get_s3_client()
        client.delete_object(
            Bucket=settings.cloudflare_r2_bucket_name,
            Key=key,
        )
        logger.info(f"Deleted from R2: {key}")
    except ClientError as e:
        logger.error(f"R2 delete failed for key '{key}': {e}", exc_info=True)


def get_presigned_url(key: str, expiry_seconds: int = 3600) -> Optional[str]:
    """Generate a presigned URL or local URL."""
    if not _is_r2_enabled():
        backend_base_url = settings.frontend_url.replace(":5173", ":8000")
        return f"{backend_base_url.rstrip('/')}/static/{key}"

    try:
        client = _get_s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.cloudflare_r2_bucket_name,
                "Key": key,
            },
            ExpiresIn=expiry_seconds,
        )
        return url
    except ClientError as e:
        logger.error(f"Presigned URL generation failed: {e}")
        return None

