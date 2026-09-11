
import logging
import re
import time
from datetime import datetime

from google import genai
from google.genai import types
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig, GenericProxyConfig

from .youtube import fetch_channel_uploads
from .config import (
    GEMINI_API_KEY,
    WEBSHARE_PROXY_USERNAME, WEBSHARE_PROXY_PASSWORD, YT_PROXY_URL,
)
from .models import Pick, NotableExtraction, User, UFCEvent
from part_2.career import normalize_name

log = logging.getLogger(__name__)


def _proxy_mode() -> str:
    """Which egress path transcript requests take. Logged on failure: a block
    while routed through Webshare and a block with no proxy at all look the
    same from the exception, but mean opposite things — the first is a bad
    Webshare package (their "Proxy Server" tier is datacenter IPs, which
    YouTube blocks exactly like Railway's; only "Residential" works), the
    second is env vars not reaching the app."""
    if WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD:
        return "webshare"
    if YT_PROXY_URL:
        return "generic-proxy"
    return "direct (no proxy configured)"


def _yt_api() -> YouTubeTranscriptApi:
    """YouTubeTranscriptApi, routed through a residential proxy when one is
    configured"""
    if WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD:
        return YouTubeTranscriptApi(proxy_config=WebshareProxyConfig(
            proxy_username=WEBSHARE_PROXY_USERNAME,
            proxy_password=WEBSHARE_PROXY_PASSWORD,
        ))
    if YT_PROXY_URL:
        return YouTubeTranscriptApi(proxy_config=GenericProxyConfig(
            http_url=YT_PROXY_URL, https_url=YT_PROXY_URL,
        ))
    return YouTubeTranscriptApi()


# Why these are named individually: this used to be a bare `except Exception:
# return None`, so an IP block and a video with captions genuinely turned off
# both surfaced as "no transcript available". Those need opposite responses —
# one is an infra fix, the other is nothing to fix — and the log gave no way to
# tell them apart.
#
# Blocking is volume-triggered, not datacenter-only: an ordinary residential IP
# earned IpBlocked after ~15 fetches while debugging this, on videos that had
# succeeded minutes earlier. So a block says nothing on its own about WHERE the
# request came from — read it together with the [via ...] mode below.
_TRANSCRIPT_ERRORS = {
    "RequestBlocked": "youtube blocked the request (rate/reputation)",
    "IpBlocked": "youtube blocked this IP (rate/reputation)",
    "TranscriptsDisabled": "uploader disabled captions",
    "NoTranscriptFound": "no captions in a requested language",
    "VideoUnavailable": "video unavailable (private/deleted)",
    "VideoUnplayable": "video unplayable",
    "AgeRestricted": "age-restricted, needs authentication",
    "PoTokenRequired": "youtube demanded a proof-of-origin token",
    "InvalidVideoId": "malformed video id",
}


def get_transcript(video_id: str) -> tuple[str | None, str]:
    """Returns (text, reason). `reason` is only meaningful when text is None."""
    try:
        fetched = _yt_api().fetch(video_id)
        text = " ".join(snippet.text for snippet in fetched).strip()
        if text:
            return text, ""
        return None, "transcript was empty"
    except Exception as e:
        name = type(e).__name__
        mode = _proxy_mode()
        reason = _TRANSCRIPT_ERRORS.get(name, f"transcript fetch failed: {name}")
        reason = f"{reason} [via {mode}]"
        log.warning("transcript fetch failed for %s: %s via %s (%s)",
                    video_id, name, mode, reason)
        return None, reason

_STOP = {"ufc", "fight", "night", "full", "card", "predictions", "prediction",
         "vs", "and", "the", "center", "centre", "arena", "stadium", "at", "co"}


def _event_number(text: str) -> str | None:
    m = re.search(r"ufc[\s-]*(\d{2,4})\b", text.lower())
    return m.group(1) if m else None


def _last_names(fighters) -> set[str]:
    out = set()
    for f in fighters:
        parts = normalize_name(f).split()
        if parts:
            out.add(parts[-1])
    return out


def distinctive_words(*texts) -> set[str]:
    """Words that occur in the text"""
    words = set()
    for text in texts:
        for word in normalize_name(text or "").split():
            if len(word) > 3 and word not in _STOP and not word.isdigit():
                words.add(word)
    return words


def find_prediction_video(channel_id: str, event) -> dict | None:
    """Best-matching prediction video for `event` on the channel, or None.
    Multi-signal scoring"""
    try:
        uploads = fetch_channel_uploads(channel_id, limit=30)
    except Exception:
        return None
    if not uploads:
        return None

    fights = list(event.fights)
    ev_num = _event_number(f"{event.title} {event.event_link}") #exctract numbers

   
    main_ln = {ln for ln in _last_names(re.split(r"\bvs\.?\b", event.title)) if len(ln) >= 3}
    all_ln = {ln for ln in _last_names([f.fighter_a for f in fights] + [f.fighter_b for f in fights]) if len(ln) >= 3}
    other_ln = all_ln - main_ln                                    # non-headliner card surnames
    venue_words = {w for w in distinctive_words(event.venue) if len(w) >= 4}
    ev_date = event.date

    best, best_total = None, 0
    for video in uploads:
        title = normalize_name(video["title"])
        title_words = set(title.split())   # WHOLE words — so 'ce' can't match 'chance'

        # date sanity: prediction videos come out shortly before the event.
        days_before = None
        if video["published_at"] and ev_date:
            try:
                pub = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00")).timestamp()
                days_before = (ev_date - pub) / 86400
            except Exception:
                days_before = None
            if days_before is not None and (days_before < -14 or days_before > 120): # no farther than 120 days
                continue  # far outside the plausible window — skip

        # WHICH event is this about? (required). Whole-word matches only.
        specific = 0
        if ev_num and re.search(rf"ufc\s*{ev_num}\b", title):
            specific += 6                                  # exact event number = strongest, unambiguous id
        specific += 2 * len(main_ln & title_words)         # headliner surname
        specific += 1 * len(other_ln & title_words)        # other card surname
        specific += 1 * len(venue_words & title_words)     # distinctive venue word
        if specific == 0:
            continue  # not about this event

        #is it a full card predciton video? sometimes youtubers make rant vids
        total = specific
        if "full card" in title:
            total += 4
        if "breakdown" in title:
            total += 3
        if "predictions" in title:      # plural = the whole card
            total += 3
        elif "prediction" in title:     # singular = often just one fight
            total += 2
        if days_before is not None and -3 <= days_before <= 21:
            total += 2

        if total > best_total:
            best, best_total = video, total

    return best


_client = None


def _gemini():
    """Gemini client with retries on transient upstream failures.
    google llm sometimes gets overloaded and return a 503 sever error. so we rety at least 5 itmes
    """
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=3,
                    initial_delay=1.0,
                    exp_base=2.0,
                    max_delay=8.0,
                    jitter=1.0,
                    http_status_codes=[408, 500, 502, 503, 504],
                ),
            ),
        )
    return _client


def is_configured() -> bool:
    return bool(GEMINI_API_KEY)


# One extracted pick per fight. fighter_a/fighter_b are echoed back so we can
# align the result to the card; predicted_winner is one of them, or null.
class _FightPick(BaseModel):
    fighter_a: str
    fighter_b: str
    predicted_winner: str | None


class _Predictions(BaseModel):
    picks: list[_FightPick]


_PROMPT = (
    "You extract a UFC pundit's fight predictions from a video transcript. "
    "You are given the fight card and the transcript. For EACH fight on the card, "
    "decide which fighter the speaker predicted to WIN. Rules:\n"
    "- predicted_winner must be EXACTLY one of the two fighter names given for that "
    "fight, or null.\n"
    "- Use only what the transcript actually says. If the speaker did not give a clear "
    "pick for a fight, return null — do not guess.\n"
    "- Return every fight from the card, in the same order."
)


def extract_picks(transcript: str, fights: list[dict]) -> list[dict]:
    card_lines = "\n".join(
        f"{i+1}. {fight['fighter_a']} vs {fight['fighter_b']}" for i, fight in enumerate(fights)
    )
    user = (
        f"FIGHT CARD:\n{card_lines}\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    resp = _gemini().models.generate_content(
        model="gemini-3.6-flash",
        contents=user,
        config={
            "system_instruction": _PROMPT,
            "response_mime_type": "application/json",
            "response_schema": _Predictions,
        },
    )
    parsed: _Predictions = resp.parsed
    return [p.model_dump() for p in parsed.picks]


# save picks — match names  fights, upsert Picks 
def _save_picks(db, user_id: int, event, extracted: list[dict]) -> dict:
    """Turn extracted {fighter_a, fighter_b, predicted_winner} into Pick rows for
    user_id. Matches each pick back to a real fight by normalized fighter pair
    (order-independent) and the winner to that fight's stored name. Upserts, so
    re-running updates rather than duplicates. Returns a review summary."""
    # normalized fighter-pair -> the real fight
    pair_map = {
        frozenset({normalize_name(fight.fighter_a), normalize_name(fight.fighter_b)}): fight
        for fight in event.fights
    }

    created = updated = no_pick = unmatched = 0
    handled = set()   # fight ids already processed this batch
    for extracted_fight in extracted:
        winner = extracted_fight.get("predicted_winner")
        if not winner:
            no_pick += 1
            continue
        fight = pair_map.get(frozenset({normalize_name(extracted_fight["fighter_a"]), normalize_name(extracted_fight["fighter_b"])}))
        if fight is None:
            unmatched += 1
            continue
       
        if fight.id in handled:
            continue
        handled.add(fight.id)
        winners_name = normalize_name(winner)
        if winners_name == normalize_name(fight.fighter_a):
            picked = fight.fighter_a
        elif winners_name == normalize_name(fight.fighter_b):
            picked = fight.fighter_b
        else:
            unmatched += 1   # LLM returned a name that's neither corner
            continue
        # indempontency guard
        existing = db.query(Pick).filter_by(user_id=user_id, fight_id=fight.id).first()
        if existing:
            if existing.picked != picked:
                existing.picked = picked
                updated += 1
        else:
            db.add(Pick(user_id=user_id, fight_id=fight.id, picked=picked))
            created += 1

    return {"created": created, "updated": updated, "no_pick": no_pick, "unmatched": unmatched}


def _save_source_video(db, user_id: int, event_id: int, video_id: str) -> None:
    existing = db.query(NotableExtraction).filter_by(user_id=user_id, event_id=event_id).first()
    if existing:
        existing.video_id = video_id
    else:
        db.add(NotableExtraction(user_id=user_id, event_id=event_id, video_id=video_id))


def run_extraction(db, user, event, video_id: str | None = None) -> dict:
  
    if not is_configured():
        return {"ok": False, "reason": "GEMINI_API_KEY not configured"}
    if not video_id and not user.youtube_channel_id:
        return {"ok": False, "reason": "user has no linked YouTube channel"}

    vid = video_id
    if not vid:
        match = find_prediction_video(user.youtube_channel_id, event)
        if not match:
            return {"ok": False, "reason": "no matching prediction video found"}
        vid = match["video_id"]

    transcript, reason = get_transcript(vid)
    if not transcript:
        return {"ok": False, "reason": reason, "video_id": vid}

    fights = [{"fighter_a": f.fighter_a, "fighter_b": f.fighter_b} for f in event.fights]
    try:
        extracted = extract_picks(transcript, fights)
    except Exception as e:
        # `ServerError` alone was unactionable — it covers an overloaded model,
        # a bad key and a malformed request alike. The status code separates
        # "retry later" from "you broke something".
        code = getattr(e, "code", None) or getattr(e, "status", None)
        detail = {
            429: "gemini quota exhausted (free tier is 20 requests/day)",
            503: "gemini overloaded (transient, retried and still failed)",
        }.get(code, f"{type(e).__name__}" + (f" {code}" if code else ""))
        log.warning("extraction failed for %s: %s: %s", vid, detail, str(e)[:300])
        return {"ok": False, "reason": f"extraction failed: {detail}", "video_id": vid}

    summary = _save_picks(db, user.id, event, extracted)
    _save_source_video(db, user.id, event.id, vid)
    db.commit()
    return {"ok": True, "video_id": vid, **summary}


def run_extraction_sweep(db, within_days: int = 10, reextract: bool = False) -> dict:
    """Cron entrypoint: run the AI pipeline across ALL upcoming events (within
    `within_days`) x all notable pundits. Idempotent and self-healing, so a
    scheduler can safely hit this daily. `reextract=True` forces already-done
    pairs to be redone."""
    now = int(time.time())
    horizon = now + within_days * 86400
    events = (
        db.query(UFCEvent)
        .filter(UFCEvent.date > now, UFCEvent.date <= horizon)
        .order_by(UFCEvent.date)
        .all()
    )
    # Skip "Road to UFC" events — the title is just fighter names, so match the
    # URL slug, which is what carries the "road-to-ufc" marker.
    events = [e for e in events if "road-to-ufc" not in (e.event_link or "").lower()]
    pundits = (
        db.query(User)
        .filter(User.is_notable.is_(True), User.youtube_channel_id.isnot(None))
        .all()
    )

    tally = {"events": len(events), "pundits": len(pundits),
             "extracted": 0, "skipped": 0, "no_video": 0, "failed": 0}
    details = []
    for event in events:
        for user in pundits:
            # skip pairs we've already extracted (unless forced)
            if not reextract:
                already = (
                    db.query(NotableExtraction)
                    .filter_by(user_id=user.id, event_id=event.id)
                    .first()
                )
                if already:
                    tally["skipped"] += 1
                    continue

            try:
                res = run_extraction(db, user, event)
            except Exception as e:
                db.rollback()   # keep the session usable for the next pundit
                res = {"ok": False, "reason": f"crashed: {type(e).__name__}"}

            if res.get("ok"):
                tally["extracted"] += 1
            elif "no matching prediction video" in res.get("reason", ""):
                tally["no_video"] += 1
            else:
                tally["failed"] += 1
            details.append({"user": user.username, "event": event.title, **res})

    return {**tally, "details": details}
