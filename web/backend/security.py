import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext
from dotenv import load_dotenv


load_dotenv()

#hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # bcrypt uses salt and is inherently slow, hard for attackers

secret_key = os.getenv("JWT_SECRET")
if not secret_key:
    # PyJWT raises on a None/empty key, but only when a token is first signed —
    # so a misconfigured deploy boots clean and dies at someone's login attempt.
    raise RuntimeError("JWT_SECRET is not set — refusing to start without a signing key.")
algorithm = os.getenv("JWT_ALGORITHM", "HS256")                    
# os.getenv returns a string, so int() it before doing date math.
# Short by design: the access token can't be revoked, so its lifetime IS the
# theft window. Long sessions come from the refresh token instead.
expires_in_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

# How long a refresh chain survives with no activity. Sliding: every rotation
# issues a successor with a fresh 30 days, so an active user is never logged out.
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Grace period during which an already-rotated token is forgiven instead of being
# treated as theft. A page that fires several API calls at once sends the same
# refresh cookie on all of them; one wins the rotation and the rest would
# otherwise look like reuse and log the user out at random.
REFRESH_REUSE_GRACE_SECONDS = int(os.getenv("REFRESH_REUSE_GRACE_SECONDS", "30"))


def new_refresh_token() -> str:
    """A fresh opaque refresh token. Not a JWT: it carries no claims, it is only
    a lookup key for a server-side row, which is what makes it revocable."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hexdigest — what actually gets stored. See RefreshToken's docstring
    for why this isn't bcrypt."""
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


#dummy hash to equalize timing
DUMMY_HASH = pwd_context.hash("dummy_password_to_equalize_timing")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create a JWT token from a dictionary of claims."""
    now = datetime.now(timezone.utc)
    payload = data.copy()
    payload["exp"] = now + timedelta(minutes=expires_in_minutes)  # when it expires
    payload["iat"] = now                                          # issued-at time all part of payload
    return jwt.encode(payload, secret_key, algorithm=algorithm)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
