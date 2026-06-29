"""Event endpoints: upcoming events for the pick'em game, plus a user's
per-event stats and their list of past events."""
import time

from fastapi import APIRouter, Depends
from sqlalchemy import and_

from ..dependencies import DBDep, get_curr_user
from ..models import User, UFCEvent, UFCFight, Pick

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
    """
    q = (
    db.query(UFCFight, Pick.picked)
    .join(Pick, and_(Pick.fight_id == UFCFight.id, Pick.user_id == user_id))
    )
    # only narrow to one event when the caller asks for it; otherwise it's overall
    if event_id is not None:
        q = q.filter(UFCFight.event_id == event_id)

    rows = q.all()

    fights = []
    correct = settled = 0
    for fight, picked in rows:
        is_settled = fight.winner is not None
        is_correct = is_settled and picked == fight.winner
        if is_settled:
            settled += 1
            correct += is_correct
        #
        fights.append({
            "event_id": fight.event_id,
            "matchup": fight.matchup,
            "fighter_a": fight.fighter_a,
            "fighter_b": fight.fighter_b,
            "img_a": fight.img_a,
            "img_b": fight.img_b,
            "picked": picked,
            "winner": fight.winner,
            "correct": is_correct,
        })

    return {
        "user_id": user_id,
        "event_id": event_id,
        "picks_made": len(fights),
        "fights_settled": settled,
        "correct": correct,
        "winrate": round(correct / settled * 100, 1) if settled else None,
        "fights": fights,
    }


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
