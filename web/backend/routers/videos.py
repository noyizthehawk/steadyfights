"""Prediction-videos endpoint: thin HTTP + Redis-cache layer over the youtube
service. The service does the fetching/parsing/filtering; this owns caching and
status codes. We only serve video metadata + IDs — playback goes through
YouTube's official embed player on the frontend (ToS-compliant)."""
import json

from fastapi import APIRouter, HTTPException
from redis import RedisError

from ..redis_client import redis_client
from ..config import VIDEOS_TTL
from .. import youtube

router = APIRouter()


@router.get("/api/videos")
def get_videos(limit: int = 12):
    if not youtube.is_configured():
        raise HTTPException(status_code=503, detail="Videos not configured (set YOUTUBE_API_KEY).")

    cache_key = f"videos:{limit}"

    # serve cached on hit; fall through on miss OR Redis outage
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
            if cached is not None:
                return json.loads(cached)
        except RedisError:
            pass

    try:
        videos = youtube.fetch_prediction_videos(limit)
    except Exception:
        raise HTTPException(status_code=502, detail="Video provider unavailable.")

    payload = {"videos": videos}

    # cache the SAME (filtered) payload we return, so hits and misses match
    if redis_client is not None:
        try:
            redis_client.set(cache_key, json.dumps(payload), ex=VIDEOS_TTL)
        except RedisError:
            pass

    return payload
