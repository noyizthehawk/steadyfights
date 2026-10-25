import os

import redis

REDIS_URL = os.getenv("REDIS_URL")
redis_client = (
    redis.from_url(
        REDIS_URL,
        decode_responses=True,
        # Railway's private network can take a moment on the first connection
        # after a deploy; 0.2s made a slow first connect look like "Redis down".
        socket_connect_timeout=2,
        socket_timeout=1,             # max wait for any get/set to answer
    )
    if REDIS_URL
    else None
)


def check_redis() -> None:
    """Say plainly, at startup, whether Redis is in use. Everything that uses it
    (login/sign-up rate limits, the bio cap, the news/videos/leaderboard caches)
    quietly switches OFF without it, so this line in the logs is the only way
    to tell — before this, a missing or unreachable Redis was invisible."""
    if redis_client is None:
        print("redis: NOT configured (REDIS_URL unset) — rate limits, bio cap and caches are OFF")
        return
    host = REDIS_URL.split("@")[-1]          # never log the password
    try:
        redis_client.ping()
        print(f"redis: connected ({host})")
    except redis.RedisError as e:
        print(f"redis: configured but UNREACHABLE ({host}): {type(e).__name__}: {e} "
              "— rate limits, bio cap and caches are OFF")
