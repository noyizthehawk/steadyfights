import os
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext
from dotenv import load_dotenv


load_dotenv()

#hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # bcrypt uses salt and is inherently slow, hard for attackers

secret_key = os.getenv("JWT_SECRET")                                 
algorithm = os.getenv("JWT_ALGORITHM", "HS256")                    
# os.getenv returns a string, so int() it before doing date math.
expires_in_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


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
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
