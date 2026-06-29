"""Event endpoints: upcoming events for the pick'em game, plus a user's
per-event stats and their list of past events."""
import time

from fastapi import APIRouter, Depends
from sqlalchemy import and_

from ..dependencies import DBDep, get_curr_user
from ..models import User, UFCEvent, UFCFight, Pick
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
