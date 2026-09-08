"""Shared FastAPI dependencies, imported by the routers. Kept out of app.py so
routers depend on THIS, not on app.py (which would create circular imports)."""
'''
When a user logs in, we make a JWT token for the user (sent in a cookie to the
browser) and we additionally make a refresh token for the user and send it as a
cookie too. Before those cookies go out, we hash the refresh token, and together
with the user id, a family id and an expiry we create a row in our db. We only
ever store the hash — never the raw token, since it's a bearer credential.

Both cookies get an explicit max_age. Without one they'd be session cookies and
the browser would drop them when the browsing session ends — which desktop hides
(the window stays open for days) but phones don't, so mobile users get logged out
while a perfectly valid 30-day row sits in the db.

When 15 minutes has encompassed and another request comes in, we check a few
things, like whether the JWT is expired or not. If it isn't, we don't need to hit
the db at all — the signature proves it's ours and that's enough.

However, if it is expired, we use the second cookie: we hash the token in it and
look up the row by that hash. Four things can happen:

  - the row isn't present at all -> wrong/forged token, so we deny
  - the row is expired           -> 30 days of inactivity, session over, deny
  - the row is present but ALREADY REVOKED -> this token was already spent, so two
    copies of it exist. Unless it was revoked in the last 30 seconds (which just
    means our own page fired parallel requests and one of them won the race), we
    treat it as theft: revoke every row sharing that family id, and deny.
  - the row is present and still valid -> we mint a new JWT and a new refresh
    token, create the new row in the same family, and revoke the former row with
    replaced_by pointing at the new one.

The important part: we revoke the old row rather than delete it. Keeping it is
what leaves a tripwire — if we deleted it, a replayed token would just look like

  - the row isn't present at all -> wrong/forged token, so we deny
  - the row is expired           -> 30 days of inactivity, session over, deny
  - the row is present but ALREADY REVOKED -> this token was already spent, so two
    copies of it exist. Unless it was revoked in the last 30 seconds (which just
    means our own page fired parallel requests and one of them won the race), we
    treat it as theft: revoke every row sharing that family id, and deny.
  - the row is present and still valid -> we mint a new JWT and a new refresh
    token, create the new row in the same family, and revoke the former row with
    replaced_by pointing at the new one.

The important part: we revoke the old row rather than delete it. Keeping it is
    replaced_by pointing at the new one.

The important part: we revoke the old row rather than delete it. Keeping it is
what leaves a tripwire — if we deleted it, a replayed token would just look like
an unknown token and we'd never learn a breach happened, and the thief could keep
using the newer token for 30 days.

The family id is never used to FIND anything; the lookup is always by token_hash,
which is unique. The family id is the blast radius — what we revoke once we've
decided there's a breach.
which is unique. The family
Two things worth pairing witto 15 minutes. It's a stateful session with a 15-minute stateless cache in front of it, and the lag is just cache staleness.

Why the refresh token isn't a JWT. 
Making it one would put you back where you started — a long-lived credential nobody can cancel. It's opaque precisely so the only way to validate it is to ask the database, which is also the only way to revoke it.
'''
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
            return 

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
    db.flush()                           
    common = dict(httponly=True, samesite="lax", secure=COOKIE_SECURE)
    response.set_cookie(
        "token",
        create_access_token({"sub": user.email}),
        max_age=expires_in_minutes * 60,
        **common,
    )
    
    response.set_cookie(
        "refresh_token", raw, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400, **common
    )
    return row


def revoke_family(db: Session, family_id: str):
    """Revoke all tokens for a family. This is what logout does."""
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
