"""Shared FastAPI dependencies, imported by the routers. Kept out of app.py so
routers depend on THIS, not on app.py (which would create circular imports)."""
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Header, Cookie, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import COOKIE_SECURE
from .database import get_db
from .models import User, RefreshToken
from .security import (
    decode_token,
    create_access_token,
    new_refresh_token,
    hash_refresh_token,
    refresh_expiry,
    expires_in_minutes,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_REUSE_GRACE_SECONDS,
)
from .redis_client import redis_client
from redis import RedisError
from .config import SETTLE_SECRET

# Annotated DB session dependency used by every route that touches the database.
DBDep = Annotated[Session, Depends(get_db)]


def rate_limit(name: str, limit: int, window: int):
    # rate limit with redis, we use incr to increment counter
    def dependency(request: Request):
        if redis_client is None:
            return
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


def _utc(dt):
    """SQLite hands back naive datetimes; compare everything in UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def issue_session(db: Session, response: Response, user: User, family_id: str | None = None):
    """Set both auth cookies. A new family_id starts a fresh login; passing an
    existing one continues that rotation chain."""
    raw = new_refresh_token()
    row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw),
        family_id=family_id or str(uuid.uuid4()),
        expires_at=refresh_expiry(),      # sliding: every rotation gets a full window
    )
    db.add(row)
    db.flush()                            # need row.id for the caller's replaced_by

    # max_age matters: without it these are SESSION cookies, which the browser
    # drops when the browsing session ends. Desktop keeps a window open for days
    # so it went unnoticed, but iOS/Android end sessions aggressively (tab
    # eviction, backgrounding, memory pressure) — the phone lost the refresh
    # cookie and got logged out, while the 30-day row sat valid in the DB.
    common = dict(httponly=True, samesite="lax", secure=COOKIE_SECURE)
    response.set_cookie(
        "token",
        create_access_token({"sub": user.email}),
        max_age=expires_in_minutes * 60,
        **common,
    )
    # Deliberately NOT path-scoped. The usual advice is path="/api/refresh" so the
    # long-lived credential only ever goes to the one endpoint that needs it. That
    # requires the client to detect a 401, call /api/refresh and retry — and api.ts
    # has no single fetch wrapper to hang that on, so it would mean touching every
    # call site. Rotating inside get_curr_user instead keeps the frontend entirely
    # unaware, at the cost of this cookie riding along on every request. httponly
    # still keeps it away from JS; what we give up is the smaller blast radius.
    response.set_cookie(
        "refresh_token", raw, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400, **common
    )
    return row


def revoke_family(db: Session, family_id: str):
    """Kill every token descended from one login. Called on logout, and on reuse
    detection where it is the whole point: if a leaked token is replayed, the
    legitimate user's chain dies too and both parties must log in again."""
    now = datetime.now(timezone.utc)
    for row in db.execute(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None)
        )
    ).scalars():
        row.revoked_at = now


def _user_from_access(db: Session, token: str | None) -> User | None:
    """The happy path: a valid, unexpired access token. None means 'fall through
    to the refresh flow' — an expired token is not an error yet."""
    if not token:
        return None
    try:
        email = decode_token(token)["sub"]
    except HTTPException:
        return None
    except Exception:
        return None
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_curr_user(
    db: DBDep,
    response: Response,
    token: str = Cookie(None),
    refresh_token: str = Cookie(None),
):
    """Auth dependency. Accepts a valid access token; failing that, silently
    rotates the refresh token and issues a new pair.

    The rotation lives here rather than in a /api/refresh endpoint the client
    calls, because both tokens are httpOnly cookies the browser already sends on
    every request. That keeps the frontend completely unaware of any of this.
    """
    user = _user_from_access(db, token)
    if user is not None:
        return user

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated") # no row not authed

    now = datetime.now(timezone.utc)
    if _utc(row.expires_at) < now:
        raise HTTPException(status_code=401, detail="Session expired") # check if token is expired

    if row.revoked_at is not None:
        # Already rotated. Two very different causes, told apart by timing:
        if row.replaced_by is not None and _utc(row.revoked_at) > now - timedelta(
            seconds=REFRESH_REUSE_GRACE_SECONDS
        ):
            # a request that raced the rotation — reuse the successor, don't punish it
            successor = db.get(RefreshToken, row.replaced_by)
            if successor is not None and successor.revoked_at is None:
                response.set_cookie(
                    "token", create_access_token({"sub": row.user.email}),
                    max_age=expires_in_minutes * 60,
                    httponly=True, samesite="lax", secure=COOKIE_SECURE,
                )
                return row.user
        # otherwise a token that was already spent is being replayed: the chain leaked
        revoke_family(db, row.family_id)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    user = row.user
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    successor = issue_session(db, response, user, family_id=row.family_id)
    row.revoked_at = now
    row.replaced_by = successor.id
    db.commit()
    return user


def verify_admin_token(x_settle_token: str | None = Header(default=None)):
    """Shared gate for cron/admin endpoints (scrape + settle). Fail closed: if no
    secret is configured the endpoint is disabled entirely. The CLI scripts
    (settle.py, refresh_data.py) bypass HTTP, so they never need this."""
    if not SETTLE_SECRET or not x_settle_token or not secrets.compare_digest(x_settle_token, SETTLE_SECRET):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
