"""Event endpoints: upcoming events for the pick'em game, plus a user's
per-event stats and their list of past events."""
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_

from ..dependencies import DBDep, get_curr_user
from ..models import User, UFCEvent, UFCFight, Pick, NotableExtraction
from ..stats import compute_user_stats

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
def user_stats(user_id: int, db: DBDep, user: User = Depends(get_curr_user), event_id: int | None = None):
    """
    Stats for a specific user, optionally filtered to a specific event. Returns settled picks, correct picks, and winrate.
    The actual computation lives in stats.compute_user_stats (shared with the profile endpoint).
    """
    return compute_user_stats(db, user_id, event_id)


@router.get("/api/users/{user_id}/events")
def user_events(user_id: int, db: DBDep, user: User = Depends(get_curr_user)):
    """Past events this user made picks in, newest first. Each one is clickable
    to see the picks made."""
    now = int(time.time())
    rows = (
        db.query(UFCEvent.id, UFCEvent.title, UFCEvent.date, UFCEvent.poster)
        .join(UFCFight, UFCFight.event_id == UFCEvent.id)
        .join(Pick, and_(Pick.fight_id == UFCFight.id, Pick.user_id == user_id))
        .filter(UFCEvent.date < now)   # past events only
        .distinct()
        .order_by(UFCEvent.date.desc())
        .all()
    )
    return {
        "events": [
            {"event_id": r.id, "title": r.title, "date": r.date, "poster": r.poster}
            for r in rows
        ]
    }


@router.get("/api/users/{user_id}/events/{event_id}/card")
def user_event_card(user_id: int, event_id: int, db: DBDep,
                    user: User = Depends(get_curr_user)):
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
