"""YouTube Data API service: fetch a channel's uploads and keep only the
prediction videos. Pure domain logic — no HTTP layer and no caching (the router
owns those). Playback happens via YouTube's official embed on the frontend."""
import html

import requests

from .config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID

_API = "https://www.googleapis.com/youtube/v3/playlistItems"

# A channel's uploads playlist = its id with the "UC" prefix swapped to "UU".
UPLOADS_PLAYLIST = "UU" + YOUTUBE_CHANNEL_ID[2:] if YOUTUBE_CHANNEL_ID else None

# Titles we treat as prediction content (substring, case-insensitive).
PREDICTION_KEYWORDS = ["prediction", "vs"]


def is_configured() -> bool:
    return bool(YOUTUBE_API_KEY and UPLOADS_PLAYLIST)


def _parse(item: dict):
    """One playlistItem -> our slim video dict, or None if it has no video id."""
    sn = item.get("snippet", {})
    vid = (sn.get("resourceId") or {}).get("videoId")
    if not vid:
        return None
    thumbs = sn.get("thumbnails") or {}
    thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    return {
        "video_id": vid,
        # YouTube returns titles HTML-escaped (&amp;, &#39;); decode for display
        "title": html.unescape(sn.get("title") or ""),
        "thumbnail": thumb,
        "published_at": sn.get("publishedAt"),
    }


def _is_prediction(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in PREDICTION_KEYWORDS)


def fetch_prediction_videos(limit: int = 10) -> list[dict]:
    """Latest prediction videos from the channel's uploads. Over-fetches (50, the
    API max) then filters by title, so we can still return up to `limit` even
    though not every upload is a prediction. Raises requests exceptions on API
    failure — the caller maps those to an HTTP error."""
    resp = requests.get(_API, params={
        "part": "snippet",
        "playlistId": UPLOADS_PLAYLIST,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }, timeout=10)
    resp.raise_for_status()

    videos = (v for it in resp.json().get("items", []) if (v := _parse(it)))
    predictions = [v for v in videos if _is_prediction(v["title"])]
    return predictions[: max(1, limit)]
