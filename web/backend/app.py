"""App entry point: build the FastAPI app, wire CORS + lifespan, and mount every
router. The actual endpoint logic lives in the routers/ package; scraping and
settling live in scraping.py; shared deps in dependencies.py."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from part_2 import Prediction_model as model
from .routers import auth, predict, picks, events, friends, leaderboard, news, admin, profile, coins, groups


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Training model (one time, please wait)...")
    model.train()
    print("Model ready. API is live.")
    yield


app = FastAPI(title="UFC Fight Predictor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/api/health")
def health():
    """Quick check that the server is up."""
    return {"status": "ok"}


# Mount every domain router. Each one owns its own /api/... paths.
app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(picks.router)
app.include_router(events.router)
app.include_router(friends.router)
app.include_router(leaderboard.router)
app.include_router(news.router)
app.include_router(admin.router)
app.include_router(profile.router)
app.include_router(coins.router)
app.include_router(groups.router)
