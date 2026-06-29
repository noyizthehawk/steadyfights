"""Worldwide leaderboard endpoint (Redis-cached)."""
import json

from fastapi import APIRouter
from sqlalchemy import func, case
from redis import RedisError

from ..dependencies import DBDep
from ..models import User, UFCFight, Pick
from ..redis_client import redis_client
from ..config import LEADERBOARD_TTL

router = APIRouter()


@router.get("/api/leaderboard")
def leaderboard(db: DBDep, limit: int = 50):
    """Worldwide leaderboard.ranked by winrate over settled fights."""
    cache_key = f"leaderboard:{limit}"

    #never make redis calls, cache a hard dependency
    try:
        cached = redis_client.get(cache_key)
        if cached is not None:
            return {"leaderboard": json.loads(cached)}
    except RedisError:
        pass

    rows = (
        db.query(
            User.id,                                             # so cards can identify the user
            User.email,                                          # user email
            func.count(Pick.id).label("total_picks"),            # all picks
            func.count(UFCFight.winner).label("settled"),        # non-null winners = settled
            # when picked == winner it's a correct pick, else 0
            func.sum(case((Pick.picked == UFCFight.winner, 1), else_=0)).label("correct"),
        )
        .join(Pick, Pick.user_id == User.id)
        .join(UFCFight, Pick.fight_id == UFCFight.id)            # inner join fights on picks
        .group_by(User.id)
        .having(func.count(UFCFight.winner) >= 3)                # only users with >= 3 settled picks
        .all()
    )

    board = []
    for uid, email, total, settled, correct in rows:
        correct = correct or 0
        winrate = round(correct / settled * 100, 1) if settled else None
        board.append({
            "id": uid,                       # used to send a friend invite from a card
            "name": email.split("@")[0],     # local part only — don't expose the full email
            "total_picks": total,
            "settled": settled,
            "correct": correct,
            "winrate": winrate,
        })

    #sort it
    board.sort(
        key=lambda r: (r["winrate"] is not None, r["winrate"] or 0, r["total_picks"]),
        reverse=True,
    )
    result = board[:limit]

    # best-effort cache write — a Redis failure must not break the response
    try:
        redis_client.set(cache_key, json.dumps(result), ex=LEADERBOARD_TTL)
    except RedisError:
        pass

    return {"leaderboard": result}
