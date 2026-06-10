
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from .security import hash_password, verify_password, create_access_token
from .database import get_db
from .models import User
from sqlalchemy.orm import Session
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from part_2 import Prediction_model as model


@asynccontextmanager
async def lifespan(app: FastAPI):
   
    print("Training model (one time, please wait)...")
    model.train()
    print("Model ready. API is live.")
    yield

#load env


app = FastAPI(title="UFC Fight Predictor API", lifespan=lifespan)
DBDep = Annotated[Session, Depends(get_db)]


# The React dev server runs on a different origin (port 5173). Browsers block
# cross-origin requests unless the server opts in via CORS. This allows it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic model 

class PredictRequest(BaseModel):
    fighter_a: str
    fighter_b: str

class SignUpRequest(BaseModel):
    email: str
    password: str
@app.get("/api/health")
def health():
    """Quick check that the server is up."""
    return {"status": "ok"}


@app.get("/api/fighters")
def get_fighters():
    """List every fighter the model knows — used to fill the dropdowns."""
    return {"fighters": model.list_fighters()}


@app.post("/api/predict")
def predict(req: PredictRequest):
    """Predict a matchup. Returns win probabilities, styles, and the pick."""
    names = set(model.list_fighters())
    if req.fighter_a not in names or req.fighter_b not in names:
        raise HTTPException(status_code=404, detail="One or both fighters not found.")
    if req.fighter_a == req.fighter_b:
        raise HTTPException(status_code=400, detail="Pick two different fighters.")
    return model.predict_fight_api(req.fighter_a, req.fighter_b)

@app.post("/api/sign_up")
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


@app.post("/api/login")
def login(user: SignUpRequest, db: DBDep):
    # verify an existing user: find by email, then check the password.
    db_user = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()

    #if no user or wrong password

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Issue a signed JWT identifying this user; the client sends it on later requests.
    token = create_access_token({"sub": db_user.email})
    return {"access_token": token, "token_type": "bearer"}
    