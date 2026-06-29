"""User profile endpoint — one call that aggregates everything the profile page
shows: identity, overall stats, world rank, friends/events counts, and a few
highlights (recent form, current streak, best event)."""
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, and_, or_

from ..dependencies import DBDep, get_curr_user
from ..models import User, UFCEvent, UFCFight, Pick, Friendship
from ..stats import compute_user_stats, compute_leaderboard

router = APIRouter()


@router.get("/api/users/{user_id}/profile")
def user_profile(user_id: int, db: DBDep, user: User = Depends(get_curr_user)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # --- overall stats (reuse the shared helper; event_id=None = overall) ---
    stats = compute_user_stats(db, user_id)
    summary = {
        "total_picks": stats["picks_made"],
        "settled": stats["fights_settled"],
        "correct": stats["correct"],
        "winrate": stats["winrate"],
    }

    # user ranking in the world, none if they dot have up to 3 settled picks like usual
    board = compute_leaderboard(db)
    world_rank = None
    for i, row in enumerate(board):
        if row["id"] == user_id:
            world_rank = {"rank": i + 1, "total_ranked": len(board)}
            break

    # --- friends count (accepted, either direction) ---
    friends_count = (
        db.query(func.count(Friendship.id))
        .filter(
            Friendship.status == "accepted",
            or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
        )
        .scalar()
    )

    # --- count of past events the user made picks in ---
    now = int(time.time())
    events_count = (
        db.query(func.count(func.distinct(UFCEvent.id)))
        .join(UFCFight, UFCFight.event_id == UFCEvent.id)
        .join(Pick, and_(Pick.fight_id == UFCFight.id, Pick.user_id == user_id))
        .filter(UFCEvent.date < now)
        .scalar()
    )

    # --- one query feeds recent_form + streak + best_event ---
    # the user's SETTLED picks, most recent first: (event_id, title, was_correct)
    rows = (
        db.query(UFCEvent.id, UFCEvent.title, UFCFight.winner, Pick.picked)
        .join(UFCFight, UFCFight.id == Pick.fight_id)
        .join(UFCEvent, UFCEvent.id == UFCFight.event_id)
        .filter(Pick.user_id == user_id, UFCFight.winner.isnot(None))
        .order_by(UFCEvent.date.desc())
        .all()
    )
    results = [(r.id, r.title, r.picked == r.winner) for r in rows]

    # recent form: last 5 results, most recent first
    recent_form = ["W" if correct else "L" for _, _, correct in results[:5]]

    # current streak
    current_streak = None
    if results:
        latest = results[0][2] 
        count = 0
        for _, _, correct in results:
            if correct == latest:
                count += 1
            else:
                break
        current_streak = {"type": "win" if latest else "loss", "count": count}

    # best event: tally correct/total per event, then pick the best.
    # tie-break: winrate desc -> more settled picks -> more recent (smaller order).
    best_event = None
    if results:
        per_event = {}  # event_id -> [title, correct, total, first_seen_order]
        for order, (eid, title, correct) in enumerate(results):
            if eid not in per_event:
                per_event[eid] = [title, 0, 0, order]
            per_event[eid][1] += int(correct)
            per_event[eid][2] += 1

        best_eid = max(
            per_event,
            key=lambda eid: (
                per_event[eid][1] / per_event[eid][2],   # winrate
                per_event[eid][2],                        # total settled
                -per_event[eid][3],                       # recency (smaller order = newer)
            ),
        )
        title, c, total, _ = per_event[best_eid]
        best_event = {
            "event_id": best_eid,
            "title": title,
            "correct": c,
            "of": total,
            "winrate": round(c / total * 100, 1),
        }

    return {
        "id": target.id,                              # for the invite button on the profile
        "name": target.email.split("@")[0],           # local part only
        "member_since": int(target.created_at.timestamp()) if target.created_at else None,
        "stats": summary,
        "world_rank": world_rank,
        "friends_count": friends_count,
        "events_count": events_count,
        "recent_form": recent_form,
        "current_streak": current_streak,
        "best_event": best_event,
    }
