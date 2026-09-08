"""Auth + account endpoints: sign up, login, logout, and "who am I"."""
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from ..config import COOKIE_SECURE
from ..dependencies import DBDep, get_curr_user, rate_limit, issue_session, revoke_family
from ..models import User, RefreshToken
from ..schemas import SignUpRequest, LoginRequest
from ..security import hash_password, verify_password, DUMMY_HASH, hash_refresh_token
from ..email_sender import send_welcome_email

router = APIRouter()

#generic so the attacker can infer anyhting
GENERIC_SIGNUP_MSG = {"message": "Account created. Please log in."}


@router.post("/api/sign_up", dependencies=[Depends(rate_limit("sign_up", limit=5, window=900))])
async def sign_up(user: SignUpRequest, db: DBDep):
    # Hash FIRST, unconditionally, so the existing-email and new-email paths do
    # the same bcrypt work and take the same time (no timing enumeration).
    hashed = hash_password(user.password)

    username_taken = db.execute(
        select(User).where(func.lower(User.username) == user.username.lower())
    ).scalar_one_or_none()
    if username_taken:
        raise HTTPException(status_code=409, detail="Username already taken")

    existing = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()
    if existing:
       
        raise HTTPException(status_code=409, detail="You already have an account. Please log in.")

    new_user = User(email=user.email, hashed_password=hashed, username=user.username)
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        #preventing race bug for concurrent sign ups at the same time
        db.rollback()
        return GENERIC_SIGNUP_MSG

    # Best-effort welcome email: the account is already saved, so a failed send
    # must not break signup. Logged (not swallowed) so failures are visible.
    try:
        await send_welcome_email(new_user.email, new_user.username)
    except Exception as e:
        print(f"[welcome email failed] to={new_user.email}: {e}")

    return GENERIC_SIGNUP_MSG


@router.post("/api/login", dependencies=[Depends(rate_limit("login", limit=5, window=900))])
def login(user: LoginRequest, db: DBDep, response: Response):
    # find the user
    db_user = db.execute(
        select(User).where(func.lower(User.username) == user.username.lower())
    ).scalar_one_or_none()

    #i still verify to prevent timing attack kinda overkill but whatever
    #bcrypt is used whether the user exists or not
    if db_user:
        valid = verify_password(user.password, db_user.hashed_password)
    else:
        verify_password(user.password, DUMMY_HASH)  # burn equivalent time
        valid = False

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Start a new rotation family: a short-lived access token plus a refresh
    # token row. secure=COOKIE_SECURE -> HTTPS-only in prod, off locally.
    issue_session(db, response, db_user)
    db.commit()
    return { "message": "Login successful" }


@router.post("/api/logout")
def logout(db: DBDep, response: Response, refresh_token: str = Cookie(None)):
    """Clear both cookies AND revoke the family server-side. Deleting the cookie
    alone would leave the refresh token valid for anyone who captured it."""
    if refresh_token:
        row = db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
        ).scalar_one_or_none()
        if row is not None:
            revoke_family(db, row.family_id)
            db.commit()
    response.delete_cookie("token", samesite="lax", secure=COOKIE_SECURE)
    response.delete_cookie("refresh_token", samesite="lax", secure=COOKIE_SECURE)
    return {"message": "Logged out"}


@router.get("/api/me")
def get_me(user: User = Depends(get_curr_user)):
    return {"id": user.id, "email": user.email, "username": user.username,
            "avatar_url": user.avatar_url}
