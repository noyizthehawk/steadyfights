import redis
import os

REDIS_URL = os.getenv("REDIS_URL")
redis_client = (
    redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.2,  # max wait to establish a connection
        socket_timeout=0.5,          # max wait for any get/set to answer
    )
    if REDIS_URL
    else None
)