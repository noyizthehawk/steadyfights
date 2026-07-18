"""App entry point: build the FastAPI app, wire CORS + lifespan, and mount every
router. The actual endpoint logic lives in the routers/ package; scraping and
settling live in scraping.py; shared deps in dependencies.py."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from part_2 import Prediction_model as model
from .database import Base, engine
from .routers import auth, predict, picks, events, friends, leaderboard, news, admin, profile, coins, groups


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any missing tables before anything else touches the DB. Idempotent:
    # on an existing DB this is a no-op; on a fresh one (first Railway boot with
    # empty Postgres) it builds the whole schema. Runs before model.train() so a
    # bad DB connection fails fast instead of after minutes of training.
    Base.metadata.create_all(bind=engine)
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


# ---- Serve the built React frontend (production) ----------------------------
# `npm run build` outputs web/frontend/dist. In prod, FastAPI serves those files
# from the SAME origin as the API, so no CORS / separate host is needed. Routes
# are matched in registration order, so every /api/... above wins first; this
# catch-all only sees what's left. Unknown paths get index.html because React
# Router owns the URL bar client-side — a refresh on /leaderboard must load the
# app shell, not 404. In dev this block is inert (Vite serves the frontend).
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        candidate = FRONTEND_DIST / full_path
        # real file at top level (favicon, poster images, etc.)? serve it as-is
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
