"""Event endpoints: upcoming events for the pick'em game, plus a user's
per-event stats and their list of past events."""
import re
import time

from fastapi import APIRouter, HTTPException
from sqlalchemy import and_

from ..dependencies import DBDep
from ..models import User, UFCEvent, UFCFight, Pick, NotableExtraction
from ..stats import compute_user_stats
from part_2.career import normalize_name

router = APIRouter()


@router.get("/api/events/upcoming")
def get_upcoming_events(db: DBDep):
    #front end call this
    now = int(time.time())
    #filter by date
    events = (
        db.query(UFCEvent)
        .filter(UFCEvent.date > now)
        .order_by(UFCEvent.date)
        .all()
    )
    return {
        "events": [
            {
                "title": e.title,
                "event_link": e.event_link,
                "date": e.date,
                "venue": e.venue,
                "poster": e.poster,
                "fights": [
                    {
                        "id": f.id,
                        "matchup": f.matchup,
                        "fighter_a": f.fighter_a,
                        "fighter_b": f.fighter_b,
                        "odds_a": f.odds_a,
                        "odds_b": f.odds_b,
                        "img_a": f.img_a,
                        "img_b": f.img_b,
                    }
                    for f in e.fights
                ],
            }
            for e in events
        ]
    }


@router.get("/api/users/{user_id}/stats")
def user_stats(user_id: int, db: DBDep, event_id: int | None = None):
    """
    Public: stats for a specific user, optionally filtered to a specific event.
    Returns settled picks, correct picks, and winrate
    """
    return compute_user_stats(db, user_id, event_id)


@router.get("/api/users/{user_id}/events")
def user_events(user_id: int, db: DBDep):
    """Every event this user has picks in — BOTH upcoming (their predictions,
    pre-results) and past (their track record). Each event carries an `upcoming`
    flag so the frontend can split them into two sections. Newest first."""
    now = int(time.time())
    rows = (
        db.query(UFCEvent.id, UFCEvent.title, UFCEvent.date, UFCEvent.poster)
        .join(UFCFight, UFCFight.event_id == UFCEvent.id)
        .join(Pick, and_(Pick.fight_id == UFCFight.id, Pick.user_id == user_id))
        .distinct()
        .order_by(UFCEvent.date.desc())
        .all()
    )
    return {
        "events": [
            {
                "event_id": r.id,
                "title": r.title,
                "date": r.date,
                "poster": r.poster,
                "upcoming": r.date is not None and r.date > now,
            }
            for r in rows
        ]
    }


@router.get("/api/users/{user_id}/events/{event_id}/card")
def user_event_card(user_id: int, event_id: int, db: DBDep):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    event = db.get(UFCEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    
    picked_by_fight = dict(
        db.query(Pick.fight_id, Pick.picked)
        .join(UFCFight, UFCFight.id == Pick.fight_id)
        .filter(Pick.user_id == user_id, UFCFight.event_id == event_id)
        .all()
    )

    # the whole card, in id order, each annotated with this user's pick
    fights = (
        db.query(UFCFight)
        .filter(UFCFight.event_id == event_id)
        .order_by(UFCFight.id)
        .all()
    )
    fight_rows = []
    for f in fights:
        picked = picked_by_fight.get(f.id)
        settled = f.winner is not None
        fight_rows.append({
            "id": f.id,
            "matchup": f.matchup,
            "fighter_a": f.fighter_a,
            "fighter_b": f.fighter_b,
            "img_a": f.img_a,
            "img_b": f.img_b,
            "odds_a": f.odds_a,
            "odds_b": f.odds_b,
            "picked": picked,
            "winner": f.winner,
            "settled": settled,
            # correct is only meaningful once settled AND they made a pick
            "correct": (settled and picked == f.winner) if picked else None,
        })

    stats = compute_user_stats(db, user_id, event_id)   # picks_made/settled/correct/winrate

    extraction = (
        db.query(NotableExtraction)
        .filter_by(user_id=user_id, event_id=event_id)
        .first()
    )
    source_video = None
    if extraction:
        source_video = {
            "video_id": extraction.video_id,
            "url": f"https://www.youtube.com/watch?v={extraction.video_id}",
        }

    return {
        "user": {
            "id": target.id,
            "username": target.username,
            "avatar_url": target.avatar_url,
            "have_youtube": target.youtube_channel_id is not None,
            "youtube_channel_id": target.youtube_channel_id,
        },
        "event": {
            "id": event.id,
            "title": event.title,
            "date": event.date,
            "venue": event.venue,
            "poster": event.poster,
        },
        "source_video": source_video,
        "summary": {
            "picks_made": stats["picks_made"],
            "fights_settled": stats["fights_settled"],
            "correct": stats["correct"],
            "winrate": stats["winrate"],
        },
        "fights": fight_rows,
    }


def _main_fight(event) -> UFCFight | None:
    """The main-event fight """
    removed_vs = re.sub(r"\bvs\.?\b", " ", event.title or "", flags=re.IGNORECASE)
    title_tokens = {name for name in normalize_name(removed_vs).split() if len(name) >= 2}
    if not title_tokens: # no headliners return none
        return None
    for fight in event.fights:
        names = set(normalize_name(fight.fighter_a).split()) | set(normalize_name(fight.fighter_b).split())
        if title_tokens <= names:          # every headliner token appears in this bout
            return fight
    return None


@router.get("/api/consensus/next")
def next_event_consensus(db: DBDep):
    """Public: notable-pundit consensus for the NEXT event's MAIN EVENT. Aggregates
    the notable users' picks for that one fight into a vote split, with the count of
    how many of the tracked pundits have weighed in so far (fills through fight week)."""
    now = int(time.time())
    event = (
        db.query(UFCEvent)
        .filter(UFCEvent.date > now)
        .order_by(UFCEvent.date)
        .first()
    )
    if event is None:
        return {"event": None, "fight": None, "consensus": None}

    fight = _main_fight(event)
    event_out = {"id": event.id, "title": event.title, "date": event.date, "poster": event.poster}
    if fight is None:
        return {"event": event_out, "fight": None, "consensus": None}

    # roster = notable pundits we actually track (have a linked channel)
    roster = (
        db.query(User)
        .filter(User.is_notable.is_(True), User.youtube_channel_id.isnot(None))
        .count()
    )
    # their picks on this one fight
    picks = (
        db.query(Pick.picked, User.username, User.avatar_url)
        .join(User, User.id == Pick.user_id)
        .filter(
            Pick.fight_id == fight.id,
            User.is_notable.is_(True),
            User.youtube_channel_id.isnot(None),
        )
        .all()
    )

    a_norm, b_norm = normalize_name(fight.fighter_a), normalize_name(fight.fighter_b)
    a_votes = b_votes = 0
    voters = []
    for picked, username, avatar_url in picks:
        pn = normalize_name(picked)
        side = fight.fighter_a if pn == a_norm else fight.fighter_b if pn == b_norm else None
        if side is None:
            continue                        # a pick that isn't either corner (shouldn't happen)
        if side == fight.fighter_a:
            a_votes += 1
        else:
            b_votes += 1
        voters.append({"username": username, "avatar_url": avatar_url, "picked": side})

    voted = a_votes + b_votes
    lean = None
    if a_votes > b_votes:
        lean = fight.fighter_a
    elif b_votes > a_votes:
        lean = fight.fighter_b

    return {
        "event": event_out,
        "fight": {
            "id": fight.id,
            "fighter_a": fight.fighter_a,
            "fighter_b": fight.fighter_b,
            "img_a": fight.img_a,
            "img_b": fight.img_b,
            "odds_a": fight.odds_a,
            "odds_b": fight.odds_b,
        },
        "consensus": {
            "roster": roster,              
            "voted": voted,                 
            "a_votes": a_votes,
            "b_votes": b_votes,
            "a_pct": round(a_votes / voted * 100) if voted else 0,
            "b_pct": round(b_votes / voted * 100) if voted else 0,
            "lean": lean,                   # majority pick, null on tie / no votes
            "voters": voters,               # who picked whom (for avatars)
        },
    }
