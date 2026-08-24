
import html
import re

import requests

from .config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_IDS

_API = "https://www.googleapis.com/youtube/v3/playlistItems"
UPLOADS_PLAYLISTS = ["UU" + c[2:] for c in YOUTUBE_CHANNEL_IDS if c]
PREDICTION_KEYWORDS = ["prediction", "vs"]


def is_configured() -> bool:
    return bool(YOUTUBE_API_KEY and UPLOADS_PLAYLISTS)


def _video_metadata(item: dict):
    """parse a single video dictionary """
    video_metadata = item.get("snippet", {})
    video_id = (video_metadata.get("resourceId") or {}).get("videoId")
    if not video_id: #if there isnt a video
        return None
    thumbnails_by_quality = video_metadata.get("thumbnails") or {}
    thumbnail = (thumbnails_by_quality.get("high") or thumbnails_by_quality.get("medium") or thumbnails_by_quality.get("default") or {}).get("url")
    return {
        "video_id": video_id,
        # YouTube returns titles HTML-escaped (&amp;, &#39;); decode for display
        "title": html.unescape(video_metadata.get("title") or ""),
        "thumbnail": thumbnail,
        "channel_title":  video_metadata.get("videoOwnerChannelTitle") or video_metadata.get("channelTitle"),
        "published_at": video_metadata.get("publishedAt"),
    }


def _is_prediction(title: str) -> bool:
    title = title.lower()
    return any(keyword in title for keyword in PREDICTION_KEYWORDS)


def _fetch_playlist(playlist_id: str) -> list[dict]:
    """get videos from a channels playlist, max 50 as youtube max"""
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
    all_videos = _fetch_playlist(uploads_playlist_id)

    # parse each raw item, skipping any that fail to parse
    videos = []
    for video in all_videos:
        video_data = _video_metadata(video) #meta data for each video
        if video:
            videos.append(video_data)

    # sort newest first
    def get_published_date(video):
        return video["published_at"] or ""
    videos.sort(key=get_published_date, reverse=True)
    return videos[:limit]


def fetch_prediction_videos(limit: int = 12) -> list[dict]:
    """Get prediction videos from all channels, newest first."""
    collected: list[dict] = []
    any_ok = False
    #iterate ofver alll channels playlist ids(lucas tracy, mma gurus, etc)
    for playlist_id in UPLOADS_PLAYLISTS:
        try:
            youtuber_videos = _fetch_playlist(playlist_id)
            any_ok = True
        except Exception:
            continue  # skip this channel, keep the others
        for video in youtuber_videos:
            video_metadata = _video_metadata(video)
            if video_metadata and _is_prediction(video_metadata["title"]):
                collected.append(video_metadata)

    if not any_ok:
        raise RuntimeError("all video channels failed")

    # newest first across channels — ISO 8601 timestamps sort lexically
    collected.sort(key=lambda v: v["published_at"] or "", reverse=True)
    return collected[: max(1, limit)]


def resolve_channel_id(handle: str) -> str | None:
    """get channel id from a string"""
    channel_handle = handle.strip().lstrip("@")
    try:
        request = requests.get(f"https://www.youtube.com/@{channel_handle}", timeout=10)
        request.raise_for_status()
        m = re.search(r'"externalId":"(UC[A-Za-z0-9_-]{22})"', request.text)
        return m.group(1) if m else None
    except Exception:
        return None
