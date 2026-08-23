
import re
from datetime import datetime

import anthropic
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

from .youtube import fetch_channel_uploads
from .config import ANTHROPIC_API_KEY
from .models import Pick
from part_2.career import normalize_name

def get_transcript(video_id: str) -> str | None:
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
        text = " ".join(snippet.text for snippet in fetched).strip()
        return text or None
    except Exception:
        return None

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
    ev_num = _event_number(f"{event.title} {event.event_link}")
    all_lastnames = _last_names([f.fighter_a for f in fights] + [f.fighter_b for f in fights])
    main_lastnames = _last_names([fights[0].fighter_a, fights[0].fighter_b]) if fights else set()
    distinctive_words_set = distinctive_words(event.title, event.venue)
    ev_date = event.date  

    best, best_total = None, 0
    for video in uploads:
        title = normalize_name(video["title"])

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

        # EVENT-SPECIFIC signals (required)
        specific = 0
        if ev_num and re.search(rf"ufc\s*{ev_num}\b", title):
            specific += 5
        specific += 2 * sum(1 for ln in all_lastnames if ln and ln in title)
        specific += 2 * sum(1 for ln in main_lastnames if ln and ln in title)  # main event weighted
        specific += sum(1 for c in distinctive_words_set if c in title)
        if specific == 0:
            continue  # not about this event

        # tie-break bonuses
        total = specific
        if "prediction" in title:
            total += 2
        if days_before is not None and -3 <= days_before <= 21:
            total += 2

        if total > best_total:
            best, best_total = video, total

    return best


_client = None


def _anthropic():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def is_configured() -> bool:
    return bool(ANTHROPIC_API_KEY)


# One extracted pick per fight. fighter_a/fighter_b are echoed back so we can
# align the result to the card; predicted_winner is one of them, or null.
class _FightPick(BaseModel):
    fighter_a: str
    fighter_b: str
    predicted_winner: str | None


class _Predictions(BaseModel):
    picks: list[_FightPick]


_SYSTEM = (
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
        f"{i+1}. {f['fighter_a']} vs {f['fighter_b']}" for i, f in enumerate(fights)
    )
    user = (
        f"FIGHT CARD:\n{card_lines}\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    resp = _anthropic().messages.parse(
        model="claude-opus-4-8",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=_SYSTEM,
        messages=[{"role": "user", "content": user}],
        output_format=_Predictions,
    )
    return [p.model_dump() for p in resp.parsed_output.picks]


# ── Stage 4: save picks — match names -> fights, upsert Picks ─────────────────
def _save_picks(db, user_id: int, event, extracted: list[dict]) -> dict:
    """Turn extracted {fighter_a, fighter_b, predicted_winner} into Pick rows for
    user_id. Matches each pick back to a real fight by normalized fighter pair
    (order-independent) and the winner to that fight's stored name. Upserts, so
    re-running updates rather than duplicates. Returns a review summary."""
    # normalized fighter-pair -> the real fight
    pair_map = {
        frozenset({normalize_name(f.fighter_a), normalize_name(f.fighter_b)}): f
        for f in event.fights
    }

    created = updated = no_pick = unmatched = 0
    for p in extracted:
        winner = p.get("predicted_winner")
        if not winner:
            no_pick += 1
            continue
        fight = pair_map.get(frozenset({normalize_name(p["fighter_a"]), normalize_name(p["fighter_b"])}))
        if fight is None:
            unmatched += 1
            continue
        winners_name = normalize_name(winner)
        if winners_name == normalize_name(fight.fighter_a):
            picked = fight.fighter_a
        elif winners_name == normalize_name(fight.fighter_b):
            picked = fight.fighter_b
        else:
            unmatched += 1   # LLM returned a name that's neither corner
            continue

        existing = db.query(Pick).filter_by(user_id=user_id, fight_id=fight.id).first()
        if existing:
            if existing.picked != picked:
                existing.picked = picked
                updated += 1
        else:
            db.add(Pick(user_id=user_id, fight_id=fight.id, picked=picked))
            created += 1

    return {"created": created, "updated": updated, "no_pick": no_pick, "unmatched": unmatched}


def run_extraction(db, user, event, video_id: str | None = None) -> dict:
  
    if not is_configured():
        return {"ok": False, "reason": "ANTHROPIC_API_KEY not configured"}
    if not video_id and not user.youtube_channel_id:
        return {"ok": False, "reason": "user has no linked YouTube channel"}

    vid = video_id
    if not vid:
        match = find_prediction_video(user.youtube_channel_id, event)
        if not match:
            return {"ok": False, "reason": "no matching prediction video found"}
        vid = match["video_id"]

    transcript = get_transcript(vid)
    if not transcript:
        return {"ok": False, "reason": "no transcript available", "video_id": vid}

    fights = [{"fighter_a": f.fighter_a, "fighter_b": f.fighter_b} for f in event.fights]
    try:
        extracted = extract_picks(transcript, fights)
    except Exception as e:
        return {"ok": False, "reason": f"extraction failed: {type(e).__name__}", "video_id": vid}

    summary = _save_picks(db, user.id, event, extracted)
    db.commit()
    return {"ok": True, "video_id": vid, **summary}
