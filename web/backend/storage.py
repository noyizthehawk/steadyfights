"""
Cloudlare R2 storage for avatars and room covers.
"""
import io
import uuid

import boto3
from botocore.config import Config
from PIL import Image, ImageOps

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

# Covers are resized before storing, so the upload cap can be looser than the
# avatar one — a straight-off-the-phone photo is often 6-8 MB.
MAX_COVER_BYTES = 10 * 1024 * 1024  # 10 MB
# The widest a cover is ever drawn is the room banner (max-w-3xl, 768px), so
# 1200px still covers a 1.5x screen without shipping the full photo to the lobby.
COVER_MAX_WIDTH = 1200
# Refuse anything bigger before decoding: a tiny PNG can claim 50k x 50k pixels
# and eat gigabytes of RAM when Pillow expands it (a "decompression bomb").
Image.MAX_IMAGE_PIXELS = 40_000_000

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


def _put(key: str, data: bytes, content_type: str) -> str:
    """Store one object under a never-reused key and return its public URL."""
    _r2().put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
        # safe to cache forever: a new upload always gets a new uuid key
        CacheControl="public, max-age=31536000, immutable",
    )
    return f"{R2_PUBLIC_URL.rstrip('/')}/{key}"


def upload_avatar(user_id: int, data: bytes, content_type: str) -> str:
    """
    Upload an avatar to R2 and return its public URL.
    """
    ext = ALLOWED_IMAGE_TYPES[content_type]
    return _put(f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}", data, content_type)


def resize_cover(data: bytes) -> bytes:
    """Shrink an uploaded photo to at most COVER_MAX_WIDTH wide and re-encode it
    as WebP. Raises ValueError if the bytes aren't a readable image.

    Re-encoding also means we never store the user's original file: EXIF
    (including GPS location from phone photos) is dropped, and whatever the
    upload claimed to be, what lands in R2 is a plain WebP we produced."""
    try:
        # open() only reads the header, so the size check runs before any
        # pixels are decoded. Pillow itself only RAISES at 2x MAX_IMAGE_PIXELS
        # (between 1x and 2x it merely warns), hence the explicit check.
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > Image.MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions are too large")
        # phones store "rotate me" in EXIF instead of rotating the pixels;
        # apply it now, because the EXIF is about to be thrown away
        img = ImageOps.exif_transpose(img)

        # WebP has no CMYK/palette modes; RGBA keeps transparent PNGs transparent
        img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
        if img.width > COVER_MAX_WIDTH:
            img = img.resize(
                (COVER_MAX_WIDTH, round(img.height * COVER_MAX_WIDTH / img.width)),
                Image.LANCZOS,
            )

        out = io.BytesIO()
        img.save(out, format="WEBP", quality=80)
        return out.getvalue()
    # OSError covers unrecognised formats AND files that die mid-decode
    # (truncated uploads only fail here, once the pixels are actually read)
    except (OSError, Image.DecompressionBombError) as e:
        raise ValueError("Not a readable image") from e


def upload_room_cover(room_id: int, data: bytes) -> str:
    """Upload an already-resized cover (see resize_cover) and return its URL."""
    return _put(f"rooms/{room_id}/{uuid.uuid4().hex}.webp", data, "image/webp")
