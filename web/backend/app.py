
import sys
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from .security import hash_password, verify_password, create_access_token, decode_token
from .database import get_db
from .models import User
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import Response
from fastapi import Cookie
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apify_client import ApifyClient
import os
import json
from newsapi import NewsApiClient


from part_2 import Prediction_model as model
from part_2 import career

'''
apify_client = ApifyClient(os.environ["UFC_API_KEY"])
run_input = {
    "mode": "api_query",
    "query_type": "latest_news",
    "fighter_name": "Justin Gaethje",
    "news_limit": 10,
    "num_events": 1,
    "admin_daily_sync": False,
    "admin_decision_sync": False,
    "target_org": "UFC"
}
run = apify_client.actor("visita/fighting-intelligence-engine").call(run_input=run_input)
for item in apify_client.dataset(run.default_dataset_id).iterate_items():
    print(json.dumps(item, indent=2))
'''

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
newsapi = NewsApiClient(api_key=NEWS_API_KEY) if NEWS_API_KEY else None

@asynccontextmanager
async def lifespan(app: FastAPI):
   
    print("Training model (one time, please wait)...")
    model.train()
    print("Model ready. API is live.")
    yield

#load env
app = FastAPI(title="UFC Fight Predictor API", lifespan=lifespan)
DBDep = Annotated[Session, Depends(get_db)]


def get_curr_user(db: DBDep, token: str = Cookie(None)):
    """Auth dependency: identify the logged-in user from the `token` cookie.

    Attach with `Depends(get_curr_user)` to any endpoint that requires login
    """
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        email = payload["sub"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# Pydantic models

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

@app.get("/api/fighters/{name}/career")
def fighter_career(name: str):
    """Career rundown for one fighter: phases, trajectory, and career score."""
    data = career.career_summary_api(name)
    if data is None:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return data

@app.get("/api/news")
def get_news(q: str = "UFC"):
    if newsapi is None:
        raise HTTPException(status_code=503, detail="News API not configured (set NEWS_API_KEY).")

    query = q if "ufc" in q.lower() else f"{q} UFC"   # keep results on-topic
    try:
        result = newsapi.get_everything(
            q=query,
            language="en",
            sort_by="publishedAt",
            page_size=10,
        )
    except Exception:
        # Don't leak provider internals; just report it's unavailable.
        raise HTTPException(status_code=502, detail="News provider unavailable.")

    return {
        "query": q,
        "articles": [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "source": (a.get("source") or {}).get("name"),
                "published_at": a.get("publishedAt"),
                "image": a.get("urlToImage"),
            }
            for a in result.get("articles", [])
        ],
    }

@app.get("/api/me")
def get_me(user: User = Depends(get_curr_user)):
    return {"id": user.id, "email": user.email}

@app.post("/api/predict")
def predict(req: PredictRequest):
    """Predict a matchup. Returns win probabilities, styles, and the pick and fighhter advantages"""
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

def _run_refresh(no_scrape: bool) -> None:
    """Background task to run a full data refresh + model retrain."""
    cmd = [sys.executable, str(PROJECT_ROOT / "refresh_data.py")]
    if no_scrape:
        cmd.append("--no-scrape")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    model.train()


    