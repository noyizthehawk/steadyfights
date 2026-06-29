"""Shared FastAPI dependencies, imported by the routers. Kept out of app.py so
routers depend on THIS, not on app.py (which would create circular imports)."""
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Header, Cookie
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token
from .redis_client import redis_client
from redis import RedisError
from .config import SETTLE_SECRET

# Annotated DB session dependency used by every route that touches the database.
DBDep = Annotated[Session, Depends(get_db)]


def rate_limit(name: str, limit: int, window: int):
    # rate limit with redis, we use incr to increment counter
    def dependency(request: Request):
        ip = request.client.host
        key = f"ratelimit:{name}:{ip}"
        try:
            count = redis_client.incr(key)         # 1 on the first hit (incrementing key)
            if count == 1:
                redis_client.expire(key, window)   # first hit to start the window timer
        except RedisError:
            return  # Redis down → fail open, don't lock anyone out

        if count > limit:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")

    return dependency


def get_curr_user(db: DBDep, token: str = Cookie(None)):
    """Auth dependency that looks up the logged-in user by token.
    """
    # if there is no token, the user is not logged in
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated") #if there is not token, the user is not logged in
    try:
        payload = decode_token(token) #if no err, try to decode the token. that is the payload
        email = payload["sub"] #the emaiil for users
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    # look up the user in the db, the payload contains very minimal info to identify a suer
    user = db.execute(
        select(User).where(User.email == email) # look for user in the db
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def verify_admin_token(x_settle_token: str | None = Header(default=None)):
    """Shared gate for cron/admin endpoints (scrape + settle). Fail closed: if no
    secret is configured the endpoint is disabled entirely. The CLI scripts
    (settle.py, refresh_data.py) bypass HTTP, so they never need this."""
    if not SETTLE_SECRET or not x_settle_token or not secrets.compare_digest(x_settle_token, SETTLE_SECRET):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
