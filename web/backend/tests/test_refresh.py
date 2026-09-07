"""Tests for refresh-token rotation (dependencies.get_curr_user).

Calls the dependency FUNCTION directly with an in-memory DB and a real
fastapi Response, so the cookies it sets can be read back off the headers.
Nothing here touches app.db or the network.

Run:  .venv/bin/python -m web.backend.tests.test_refresh
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException, Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..dependencies import get_curr_user, issue_session, revoke_family
from ..models import User, RefreshToken
from ..security import (
    algorithm,
    create_access_token,
    hash_refresh_token,
    secret_key,
    REFRESH_REUSE_GRACE_SECONDS,
)


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def a_user(db):
    u = User(email="r@x.com", hashed_password="x", username="r_user")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def cookies_of(response: Response) -> dict:
    """Pull {name: value} out of the Set-Cookie headers the dependency wrote."""
    out = {}
    for header in response.headers.getlist("set-cookie"):
        name, _, rest = header.partition("=")
        out[name.strip()] = rest.split(";")[0]
    return out


def expired_access_token(email: str) -> str:
    """A real, correctly signed JWT that is simply past its exp — the state every
    user lands in 15 minutes after logging in."""
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    return jwt.encode({"sub": email, "exp": past, "iat": past}, secret_key, algorithm=algorithm)


def login(db, user):
    """Simulate a fresh login and return the raw refresh token the client holds."""
    resp = Response()
    issue_session(db, resp, user)
    db.commit()
    return cookies_of(resp)["refresh_token"]


# --------------------------------------------------------------------------- #

def test_valid_access_token_does_not_rotate():
    db = make_db()
    user = a_user(db)
    login(db, user)
    before = db.execute(select(RefreshToken)).scalars().all()

    resp = Response()
    got = get_curr_user(db, resp, token=create_access_token({"sub": user.email}), refresh_token=None)

    assert got.id == user.id
    # the fast path must not touch the DB — this runs on every authenticated request
    assert len(db.execute(select(RefreshToken)).scalars().all()) == len(before)
    assert cookies_of(resp) == {}


def test_expired_access_token_rotates_silently():
    db = make_db()
    user = a_user(db)
    raw = login(db, user)
    original = db.execute(select(RefreshToken)).scalar_one()

    resp = Response()
    got = get_curr_user(db, resp, token=expired_access_token(user.email), refresh_token=raw)
    assert got.id == user.id

    # caller gets a brand new pair
    set_cookies = cookies_of(resp)
    assert set_cookies["refresh_token"] != raw
    assert "token" in set_cookies

    # the spent token is revoked and linked forward
    db.refresh(original)
    assert original.revoked_at is not None
    assert original.replaced_by is not None

    successor = db.get(RefreshToken, original.replaced_by)
    assert successor.revoked_at is None
    assert successor.family_id == original.family_id          # same chain
    assert successor.token_hash == hash_refresh_token(set_cookies["refresh_token"])


def test_rotation_slides_the_expiry_forward():
    """30 days SLIDING: each successor gets a full window, so an active user is
    never logged out."""
    db = make_db()
    user = a_user(db)
    raw = login(db, user)
    original = db.execute(select(RefreshToken)).scalar_one()
    original.expires_at = datetime.now(timezone.utc) + timedelta(days=3)   # part-used window
    db.commit()

    get_curr_user(db, Response(), token=None, refresh_token=raw)

    successor = db.get(RefreshToken, original.replaced_by)
    assert successor.expires_at > original.expires_at


def test_reuse_of_a_spent_token_revokes_the_whole_family():
    """The point of rotating: a replayed token means two copies exist, so the
    chain is assumed stolen and every token in it dies."""
    db = make_db()
    user = a_user(db)
    raw = login(db, user)

    # legitimate rotation
    get_curr_user(db, Response(), token=None, refresh_token=raw)
    original = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw))
    ).scalar_one()
    # push it outside the grace window so this reads as a replay, not a race
    original.revoked_at = datetime.now(timezone.utc) - timedelta(
        seconds=REFRESH_REUSE_GRACE_SECONDS + 10
    )
    db.commit()

    with pytest.raises(HTTPException) as e:
        get_curr_user(db, Response(), token=None, refresh_token=raw)
    assert e.value.status_code == 401

    # the successor is collateral damage, by design: we can't tell victim from thief
    rows = db.execute(select(RefreshToken)).scalars().all()
    assert all(r.revoked_at is not None for r in rows)


def test_parallel_requests_inside_the_grace_window_are_forgiven():
    """A page firing several calls at once sends the same refresh cookie on all
    of them. One wins the rotation; the rest must not be treated as theft."""
    db = make_db()
    user = a_user(db)
    raw = login(db, user)

    get_curr_user(db, Response(), token=None, refresh_token=raw)     # request A wins

    resp = Response()
    got = get_curr_user(db, resp, token=None, refresh_token=raw)     # request B, same cookie
    assert got.id == user.id

    # B gets a fresh access token but must NOT mint a second refresh token —
    # that would clobber the successor A already issued
    assert "token" in cookies_of(resp)
    assert "refresh_token" not in cookies_of(resp)

    # and the family survives
    assert db.get(RefreshToken, 2).revoked_at is None


def test_expired_refresh_token_is_rejected():
    db = make_db()
    user = a_user(db)
    raw = login(db, user)
    row = db.execute(select(RefreshToken)).scalar_one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    with pytest.raises(HTTPException) as e:
        get_curr_user(db, Response(), token=None, refresh_token=raw)
    assert e.value.status_code == 401


def test_unknown_refresh_token_is_rejected():
    db = make_db()
    a_user(db)
    with pytest.raises(HTTPException) as e:
        get_curr_user(db, Response(), token=None, refresh_token="not-a-real-token")
    assert e.value.status_code == 401


def test_no_cookies_at_all_is_rejected():
    db = make_db()
    a_user(db)
    with pytest.raises(HTTPException) as e:
        get_curr_user(db, Response(), token=None, refresh_token=None)
    assert e.value.status_code == 401


def test_revoke_family_ends_every_session_in_the_chain():
    """What logout relies on, and what makes these sessions revocable at all —
    the thing a bare stateless JWT can't do."""
    db = make_db()
    user = a_user(db)
    raw = login(db, user)
    get_curr_user(db, Response(), token=None, refresh_token=raw)     # chain of 2

    family = db.execute(select(RefreshToken)).scalars().first().family_id
    revoke_family(db, family)
    db.commit()

    assert all(r.revoked_at is not None for r in db.execute(select(RefreshToken)).scalars())


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS   {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL   {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
