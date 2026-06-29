"""Auth + account endpoints: sign up, login, logout, and "who am I"."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from ..dependencies import DBDep, get_curr_user, rate_limit
from ..models import User
from ..schemas import SignUpRequest
from ..security import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/api/sign_up", dependencies=[Depends(rate_limit("sign_up", limit=5, window=900))])
def sign_up(user: SignUpRequest, db: DBDep):
    #check for existing user before anything else
    existing = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    #if not create new user
    new_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email}


@router.post("/api/login", dependencies=[Depends(rate_limit("login", limit=5, window=900))])
def login(user: SignUpRequest, db: DBDep, response: Response):
    # verify an existing user: find by email, then check the password.
    db_user = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()

    #if no user or wrong password

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Issue a signed JWT identifying this user; the client sends it on later requests.
    token = create_access_token({"sub": db_user.email})
    #save token
    response.set_cookie("token", token, httponly=True, samesite="lax", secure=False)
    return { "message": "Login successful" }


@router.post("/api/logout")
def logout(response: Response):
    # The token cookie is httpOnly, so JS can't clear it — the server must.
    response.delete_cookie("token", samesite="lax")
    return {"message": "Logged out"}


@router.get("/api/me")
def get_me(user: User = Depends(get_curr_user)):
    return {"id": user.id, "email": user.email}
