"""Auth + account endpoints: sign up, login, logout, and "who am I"."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from ..config import COOKIE_SECURE
from ..dependencies import DBDep, get_curr_user, rate_limit
from ..models import User
from ..schemas import SignUpRequest
from ..security import hash_password, verify_password, create_access_token, DUMMY_HASH

router = APIRouter()

#generic so the attacker can infer anyhting
GENERIC_SIGNUP_MSG = {"message": "Account created. Please log in."}


@router.post("/api/sign_up", dependencies=[Depends(rate_limit("sign_up", limit=5, window=900))])
def sign_up(user: SignUpRequest, db: DBDep):
    # Hash FIRST, unconditionally, so the existing-email and new-email paths do
    # the same bcrypt work and take the same time (no timing enumeration).
    hashed = hash_password(user.password)

    existing = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()
    if existing:
        # Don't reveal that the email is taken — return the generic response.
        return GENERIC_SIGNUP_MSG

    new_user = User(email=user.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()

    return GENERIC_SIGNUP_MSG


@router.post("/api/login", dependencies=[Depends(rate_limit("login", limit=5, window=900))])
def login(user: SignUpRequest, db: DBDep, response: Response):
    # verify an existing user: find by email, then check the password.
    db_user = db.execute(
        select(User).where(User.email == user.email)
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

    # Issue a signed JWT identifying this user; the client sends it on later requests.
    token = create_access_token({"sub": db_user.email})
    # secure=COOKIE_SECURE -> HTTPS-only in prod, off locally (plain HTTP dev).
    response.set_cookie("token", token, httponly=True, samesite="lax", secure=COOKIE_SECURE)
    return { "message": "Login successful" }


@router.post("/api/logout")
def logout(response: Response):
    # The token cookie is httpOnly, so JS can't clear it — the server must.
    # Attributes must match the ones set at login or some browsers won't clear it.
    response.delete_cookie("token", samesite="lax", secure=COOKIE_SECURE)
    return {"message": "Logged out"}


@router.get("/api/me")
def get_me(user: User = Depends(get_curr_user)):
    return {"id": user.id, "email": user.email}
