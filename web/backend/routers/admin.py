"""Admin / cron endpoints: scrape upcoming events, settle finished ones, and
manage notable users. All gated by verify_admin_token (shared secret). The CLI
scripts bypass HTTP."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from ..dependencies import DBDep, verify_admin_token
from ..models import User, UFCEvent
from ..schemas import NotableRequest, ExtractRequest
from ..security import hash_password
from ..scraping import run_settle, scrape_and_save
from .. import youtube, predictions_ai

router = APIRouter()


def _find_user(db, username: str):
    """Case-insensitive username lookup, matching the lower(username) index."""
    return db.execute(
        select(User).where(func.lower(User.username) == username.lower())
    ).scalar_one_or_none()


@router.post("/api/admin/notable/{username}", dependencies=[Depends(verify_admin_token)])
def add_notable(username: str, db: DBDep, body: NotableRequest | None = None):
    body = body or NotableRequest()

    #if there is no channel is specified, try getting it or resolving it from the handle
    channel_id = body.youtube_channel_id
    if not channel_id and body.youtube_handle:
        channel_id = youtube.resolve_channel_id(body.youtube_handle)
        if not channel_id:
            raise HTTPException(status_code=400, detail="Could not resolve YouTube handle to a channel id")

    # pull the channel's profile picture (hotlinked) so the pundit has a real avatar
    avatar = youtube.fetch_channel_avatar(channel_id) if channel_id else None

    user = _find_user(db, username)
    created = False
    #if there is no user, create one (good for popular figures that dont have an account yet)
    if user is None:
        user = User(
            username=username,
            email=f"{username.lower()}@notable.steadyfights.local",
            hashed_password=hash_password(secrets.token_urlsafe(32)),  # unusable
            is_notable=True,
            youtube_channel_id=channel_id,
            avatar_url=avatar,
        )
        db.add(user)
        created = True
    else:
        user.is_notable = True
        if channel_id:
            user.youtube_channel_id = channel_id
        if avatar:
            user.avatar_url = avatar

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists")
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "is_notable": user.is_notable,
        "youtube_channel_id": user.youtube_channel_id,
        "have_youtube": user.youtube_channel_id is not None,
        "created": created,
    }


@router.delete("/api/admin/notable/{username}", dependencies=[Depends(verify_admin_token)])
def remove_notable(username: str, db: DBDep): 
    #remov e the notable flag                  
    user = _find_user(db, username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_notable = False
    db.commit()
    return {"id": user.id, "username": user.username, "is_notable": user.is_notable}


@router.post("/api/settle-events", dependencies=[Depends(verify_admin_token)])
def settle_finished_events(db: DBDep):
    # cron-driven later; gated by verify_admin_token (shared secret).
    return {"status": "ok", **run_settle(db)}


@router.post("/api/scrape-events", dependencies=[Depends(verify_admin_token)])
def scrape_events_endpoint(db: DBDep):
   # cron later; gated by verify_admin_token so the live ufc.com scrape isn't public
    results = scrape_and_save(db)
    return {"count": len(results), "saved": True}


@router.post("/api/admin/extract-predictions", dependencies=[Depends(verify_admin_token)])
def extract_predictions(body: ExtractRequest, db: DBDep):
    """Run the AI pipeline: pull each notable YouTuber's prediction video for this
    event, extract their picks, and save them. Returns a per-user summary to
    review. """
    if body.video_id and not body.username:
        raise HTTPException(status_code=400, detail="video_id override requires a username")

    event = db.execute(
        select(UFCEvent).where(UFCEvent.event_link == body.event_link)
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if body.username:
        user = _find_user(db, body.username)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        users = [user]
    else:
        users = db.execute(
            select(User).where(User.is_notable.is_(True), User.youtube_channel_id.isnot(None))
        ).scalars().all()

    results = {
        u.username: predictions_ai.run_extraction(db, u, event, video_id=body.video_id)
        for u in users
    }
    return {"event": event.title, "results": results}


@router.post("/api/admin/extract-predictions/sweep", dependencies=[Depends(verify_admin_token)])
def extract_predictions_sweep(db: DBDep, within_days: int = 10, reextract: bool = False):
    """Cron entrypoint: run the AI pipeline across ALL upcoming events (within
    `within_days`) x all notable pundits. Idempotent and self-healing, so a
    scheduler can safely hit this daily. `reextract=True` forces already-done
    pairs to be redone."""
    return predictions_ai.run_extraction_sweep(db, within_days=within_days, reextract=reextract)
