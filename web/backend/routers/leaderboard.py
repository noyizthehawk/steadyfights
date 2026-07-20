"""Worldwide leaderboard endpoint (Redis-cached). The ranking math lives in
stats.compute_leaderboard (shared with the profile's world-rank)."""
import json

from fastapi import APIRouter
from redis import RedisError

from ..dependencies import DBDep
from ..redis_client import redis_client
from ..config import LEADERBOARD_TTL
from ..stats import compute_leaderboard

router = APIRouter()


@router.get("/api/leaderboard")
def leaderboard(db: DBDep, limit: int = 50):
    """Worldwide leaderboard.ranked by winrate over settled fights."""
    cache_key = f"leaderboard:{limit}"

    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
            if cached is not None:
                return {"leaderboard": json.loads(cached)}
        except RedisError:
            pass

    result = compute_leaderboard(db)[:limit]

    if redis_client is not None:
        try:
            redis_client.set(cache_key, json.dumps(result), ex=LEADERBOARD_TTL)
        except RedisError:
            pass

    return {"leaderboard": result}
