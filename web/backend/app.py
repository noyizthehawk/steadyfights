
import sys
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from .security import hash_password, verify_password, create_access_token, decode_token
from .database import get_db, SessionLocal, Base
from .models import User, UFCEvent, UFCFight, Pick
from sqlalchemy.orm import Session, relationship
from sqlalchemy import select, func, case
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
import requests
import unicodedata
from datetime import datetime, timedelta, timezone
from newsapi import NewsApiClient
from bs4 import BeautifulSoup
from part_2 import Prediction_model as model
from part_2 import career
import time
from sqlalchemy import Column, String, Integer, JSON, ForeignKey




BASE = "https://www.ufc.com"
headers = {"User-Agent": "Mozilla/5.0"}

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
newsapi = NewsApiClient(api_key=NEWS_API_KEY) if NEWS_API_KEY else None

#FUTURE FIGHTS API
UFC_API_KEY = os.getenv("UFC_API_KEY")
client = ApifyClient(UFC_API_KEY)

def _norm_name(s):
    """Lowercase + strip accents so 'Jiří Procházka' matches 'Jiri Prochazka'."""
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()

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
    """Auth dependency that looks up the logged-in user by token.
    """
    # if there is no token, the user is not logged in
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

class PickRequest(BaseModel):
    fight_id: int
    picked: str
@app.get("/api/health")
def health():
    """Quick check that the server is up."""
    return {"status": "ok"}


@app.get("/api/fighters")
def get_fighters():
    """List every fighter the model knows about, used to fill the dropdowns."""
    return {"fighters": model.list_fighters()}

@app.get("/api/fighters/{name}/career")
def fighter_career(name: str):
    """Career rundown for one fighter: phases, trajectory, and career score."""
    data = career.career_summary_api(name)
    if data is None:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return data
def save_events(results: list, db: Session):
    for r in results:
        # Find the existing event, or create a new one. We UPDATE existing events
        # rather than skipping them, so a card that firms up (main event announced,
        # title changes from "TBD vs TBD", odds posted) actually refreshes.
        event = db.query(UFCEvent).filter_by(event_link=r["event_link"]).first()
        if event is None:
            event = UFCEvent(event_link=r["event_link"])
            db.add(event)

        event.title = r["title"]
        event.date = r["date"]
        event.venue = r["venue"]
        event.poster = r["poster"]

        # Upsert fights keyed on matchup. We never DELETE fight rows here so that
        # any picks referencing them stay valid (stale/cancelled bouts can be
        # cleaned up separately later).
        existing_fights = {f.matchup: f for f in event.fights}
        for f in r["fights"]:
            fight = existing_fights.get(f["matchup"])
            if fight is None:
                event.fights.append(UFCFight(
                    matchup=f["matchup"],
                    fighter_a=f["fighter_a"],
                    fighter_b=f["fighter_b"],
                    odds_a=f["odds_a"],
                    odds_b=f["odds_b"],
                    img_a=f["img_a"],
                    img_b=f["img_b"],
                ))
            else:
                # refresh the volatile fields on a bout we've already stored
                fight.odds_a = f["odds_a"]
                fight.odds_b = f["odds_b"]
                fight.img_a = f["img_a"]
                fight.img_b = f["img_b"]
    db.commit()
    
def _clean_odds(text):
    text = text.strip()
    return text if text not in ("", "-") else None


def scrape_event_details(event_url):
    #visit individual event
    res = requests.get(BASE + event_url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    #poster — .c-hero__image is a wrapper div; the real event art is the <img> inside it
    poster_img = soup.select_one(".c-hero__image img")
    poster = poster_img["src"] if poster_img and poster_img.has_attr("src") else None

    fights = []
    for bout in soup.select(".c-listing-fight"):
        names = [n.get_text(" ", strip=True) for n in bout.select(".c-listing-fight__corner-name")]
        odds = [o.get_text(strip=True) for o in bout.select(".c-listing-fight__odds-amount")]
        if len(names) < 2:
            continue  # skip incomplete blocks 

        fighter_a, fighter_b = names[0], names[1]
        odds_a = _clean_odds(odds[0]) if len(odds) >= 2 else None
        odds_b = _clean_odds(odds[1]) if len(odds) >= 2 else None

        # fighter headshots — scoped to the red/blue corner so we skip the flag imgs
        img_a_el = bout.select_one(".c-listing-fight__corner-image--red img")
        img_b_el = bout.select_one(".c-listing-fight__corner-image--blue img")
        img_a = img_a_el["src"] if img_a_el and img_a_el.has_attr("src") else None
        img_b = img_b_el["src"] if img_b_el and img_b_el.has_attr("src") else None

        fights.append({
            "matchup": f"{fighter_a} vs {fighter_b}",
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "odds_a": odds_a,
            "odds_b": odds_b,
            "img_a": img_a,
            "img_b": img_b,
        })

    return poster, fights
def scrape_events():
    html_data = requests.get(BASE + "/events", headers=headers, timeout=10).text
    soup = BeautifulSoup(html_data, "html.parser")

    results = []
    for event in soup.find_all("div", class_="l-listing__item"):
        article = event.find("article", class_="c-card-event--result")
        if not article:
            continue
        #healdine and other improtant stuff
        headline = article.find("h3", class_="c-card-event--result__headline")
        title = headline.find("a").text.strip() if headline else None
        event_link = headline.find("a")["href"] if headline else None

        #date
        date_div = article.find("div", class_="c-card-event--result__date")
        timestamp = date_div.get("data-main-card-timestamp") if date_div else None
        if timestamp and int(timestamp) < time.time():
            continue
         # Venue
        location = article.find("div", class_="c-card-event--result__location")
        venue = location.find("h5").text.strip() if location else None

        # The bouts (names + odds) come from the event's detail page, where
        poster, fights = scrape_event_details(event_link) if event_link else (None, [])
        time.sleep(1)
        results.append({
            "title": title,
            "event_link": event_link,
            "date": timestamp,
            "venue": venue,
            "poster": poster,
            "fights": fights,
        })
    return results
def scrape_and_save(db: Session):
    results = scrape_events()   
    save_events(results, db)
    return results
@app.post("/api/scrape-events")
def scrape_events_endpoint(db: DBDep):
   # cron later
    results = scrape_and_save(db)
    return {"count": len(results), "saved": True}


@app.get("/api/events/upcoming")
def get_upcoming_events(db: DBDep):
    #front end call this
    now = int(time.time())
    #filter by date
    events = (
        db.query(UFCEvent)
        .filter(UFCEvent.date > now)
        .order_by(UFCEvent.date)
        .all()
    )
    return {
        "events": [
            {
                "title": e.title,
                "event_link": e.event_link,
                "date": e.date,
                "venue": e.venue,
                "poster": e.poster,
                "fights": [
                    {
                        "id": f.id,
                        "matchup": f.matchup,
                        "fighter_a": f.fighter_a,
                        "fighter_b": f.fighter_b,
                        "odds_a": f.odds_a,
                        "odds_b": f.odds_b,
                        "img_a": f.img_a,
                        "img_b": f.img_b,
                    }
                    for f in e.fights
                ],
            }
            for e in events
        ]
    }


@app.post("/api/picks")
def make_pick(req: PickRequest, db: DBDep, user: User = Depends(get_curr_user)):
    # Make a pick
    fight = db.get(UFCFight, req.fight_id)
    if fight is None:
        raise HTTPException(status_code=404, detail="Fight not found")

    # `picked` must be one of the two fighters in this bout
    if req.picked not in (fight.fighter_a, fight.fighter_b):
        raise HTTPException(status_code=400, detail="Picked fighter is not in this fight")

    # Picks lock at the event's start time
    if fight.event and fight.event.date and fight.event.date <= int(time.time()):
        raise HTTPException(status_code=403, detail="Picks are locked for this event")

    # Upsert: update the existing pick, or insert a new one
    pick = db.execute(
        select(Pick).where(Pick.user_id == user.id, Pick.fight_id == req.fight_id)
    ).scalar_one_or_none()
    if pick:
        pick.picked = req.picked
    else:
        pick = Pick(user_id=user.id, fight_id=req.fight_id, picked=req.picked)
        db.add(pick)
    db.commit()
    return {"fight_id": req.fight_id, "picked": req.picked}


@app.get("/api/picks/me")
def my_picks(db: DBDep, user: User = Depends(get_curr_user)):
    """The logged-in user's picks, keyed by fight_id — used to pre-fill the buttons."""
    picks = db.execute(select(Pick).where(Pick.user_id == user.id)).scalars().all()
    return {"picks": {p.fight_id: p.picked for p in picks}}


@app.get("/api/picks/me/stats")
def my_stats(db: DBDep, user: User = Depends(get_curr_user)):
    """Derived winrate over SETTLED fights only."""
    rows = (
        db.query(Pick.picked, UFCFight.winner)
        .join(UFCFight, Pick.fight_id == UFCFight.id)
        .filter(Pick.user_id == user.id, UFCFight.winner.isnot(None))
        .all()
    )
    settled = len(rows)
    correct = sum(1 for picked, winner in rows if picked == winner)
    winrate = round(correct / settled * 100, 1) if settled else None
    return {"settled": settled, "correct": correct, "winrate": winrate}


@app.get("/api/leaderboard")
def leaderboard(db: DBDep, limit: int = 50):
    """Worldwide leaderboard.ranked by winrate over settled fights."""
    rows = (
        db.query(
            User.email,                                          # user email
            func.count(Pick.id).label("total_picks"),            # all picks
            func.count(UFCFight.winner).label("settled"),        # non-null winners = settled
            # when picked == winner it's a correct pick, else 0
            func.sum(case((Pick.picked == UFCFight.winner, 1), else_=0)).label("correct"),
        )
        .join(Pick, Pick.user_id == User.id)
        .join(UFCFight, Pick.fight_id == UFCFight.id)            # inner join fights on picks
        .group_by(User.id)
        .having(func.count(UFCFight.winner) >= 3)                # only users with >= 3 settled picks
        .all()
    )

    board = []
    for email, total, settled, correct in rows:
        correct = correct or 0
        winrate = round(correct / settled * 100, 1) if settled else None
        board.append({
            # local only
            "name": email.split("@")[0],
            "total_picks": total,
            "settled": settled,
            "correct": correct,
            "winrate": winrate,
        })

    #sort it
    board.sort(
        key=lambda r: (r["winrate"] is not None, r["winrate"] or 0, r["total_picks"]),
        reverse=True,
    )
    return {"leaderboard": board[:limit]}


       
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


@app.post("/api/logout")
def logout(response: Response):
    # The token cookie is httpOnly, so JS can't clear it — the server must.
    response.delete_cookie("token", samesite="lax")
    return {"message": "Logged out"}

def _run_refresh(no_scrape: bool) -> None:
    """Background task to run a full data refresh + model retrain."""
    cmd = [sys.executable, str(PROJECT_ROOT / "refresh_data.py")]
    if no_scrape:
        cmd.append("--no-scrape")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    model.train()
