"""
Cloudlare R2 storage for avatars.
"""
import uuid

import boto3
from botocore.config import Config

from .config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
)

# Allowed avatar types file extension used in the object key.
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB

# Built lazily so the app still boots when R2 isn't configured (e.g. a dev box
# without credentials) — only the upload endpoint needs it.
_client = None


def _r2():
    global _client
    if _client is None:
        if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL]):
            raise RuntimeError("R2 is not configured (missing R2_* env vars)")
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


def upload_avatar(user_id: int, data: bytes, content_type: str) -> str:
    """Store an avatar image in R2 and return its public URL.

    A fresh UUID key per upload means each new avatar gets a new URL, so browsers
    never show a stale cached image. (Old objects are left behind — cheap, and a
    cleanup pass can prune them later.)
    """
    ext = ALLOWED_IMAGE_TYPES[content_type]
    key = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"
    _r2().put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )
    return f"{R2_PUBLIC_URL.rstrip('/')}/{key}"
