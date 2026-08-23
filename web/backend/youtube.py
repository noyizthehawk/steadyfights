
import html
import re

import requests

from .config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_IDS

_API = "https://www.googleapis.com/youtube/v3/playlistItems"

# A channel's uploads playlist = its id with the "UC" prefix swapped to "UU".
UPLOADS_PLAYLISTS = ["UU" + c[2:] for c in YOUTUBE_CHANNEL_IDS if c]

# Titles we treat as prediction content (substring, case-insensitive).
PREDICTION_KEYWORDS = ["prediction", "vs"]


def is_configured() -> bool:
    return bool(YOUTUBE_API_KEY and UPLOADS_PLAYLISTS)


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
        "channel_title": sn.get("videoOwnerChannelTitle") or sn.get("channelTitle"),
        "published_at": sn.get("publishedAt"),
    }


def _is_prediction(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in PREDICTION_KEYWORDS)


def _fetch_playlist(playlist_id: str) -> list[dict]:
    resp = requests.get(_API, params={
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json().get("items", [])


def fetch_channel_uploads(channel_id: str, limit: int = 30) -> list[dict]:
    """Recent uploads (parsed, unfiltered) for ONE channel, newest first — used
    to match a prediction video to an event. Raises on API failure."""
    uploads_playlist_id = "UU" + channel_id[2:]
    items = _fetch_playlist(uploads_playlist_id)

    # parse each raw item, skipping any that fail to parse
    videos = []
    for item in items:
        parsed = _parse(item)
        if parsed:
            videos.append(parsed)

    # sort newest first
    def get_published_date(video):
        return video["published_at"] or ""
    videos.sort(key=get_published_date, reverse=True)

    return videos[:limit]


def fetch_prediction_videos(limit: int = 12) -> list[dict]:
    # fetch all playlistItems, filter to prediction videos
    collected: list[dict] = []
    any_ok = False
    for playlist_id in UPLOADS_PLAYLISTS:
        try:
            items = _fetch_playlist(playlist_id)
            any_ok = True
        except Exception:
            continue  # skip this channel, keep the others
        for it in items:
            v = _parse(it)
            if v and _is_prediction(v["title"]):
                collected.append(v)

    if not any_ok:
        raise RuntimeError("all video channels failed")

    # newest first across channels — ISO 8601 timestamps sort lexically
    collected.sort(key=lambda v: v["published_at"] or "", reverse=True)
    return collected[: max(1, limit)]


def resolve_channel_id(handle: str) -> str | None:
    """get channel id from a string"""
    h = handle.strip().lstrip("@")
    try:
        r = requests.get(f"https://www.youtube.com/@{h}", timeout=10)
        r.raise_for_status()
        m = re.search(r'"externalId":"(UC[A-Za-z0-9_-]{22})"', r.text)
        return m.group(1) if m else None
    except Exception:
        return None
