"""Fighter + prediction endpoints: list fighters, career summaries, top careers,
and the head-to-head prediction itself."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_

from ..dependencies import get_curr_user, DBDep
from ..models import User, UFCFight, UFCEvent
from ..schemas import PredictRequest, DreamRequest
from part_2 import Prediction_model as model
from part_2 import career
from part_2.career import normalize_name

router = APIRouter()


def _fighter_image(db, name: str):
    target = normalize_name(name)
    fights = (
        db.query(UFCFight)
        .join(UFCEvent, UFCFight.event_id == UFCEvent.id)
        .filter(or_(UFCFight.img_a.isnot(None), UFCFight.img_b.isnot(None)))
        .order_by(UFCEvent.date.desc())
        .all()
    )
    for f in fights:
        if f.img_a and f.fighter_a and normalize_name(f.fighter_a) == target:
            return f.img_a
        if f.img_b and f.fighter_b and normalize_name(f.fighter_b) == target:
            return f.img_b
    return None


@router.get("/api/fighters")
def get_fighters():
    """List every fighter the model knows about this is used to fill the dropdowns
    """
    return {"fighters": model.list_fighters()}


@router.get("/api/fighters/{name}/career")
def fighter_career(name: str, db: DBDep):
    """Career rundown for one fighter: phases, trajectory, and career score."""
    data = career.career_summary_api(name)
    if data is None:
        raise HTTPException(status_code=404, detail="Fighter not found")
    data["image_url"] = _fighter_image(db, name)  
    return data


@router.get("/api/careers/top")
def top_careers_endpoint(n: int = 10, min_fights: int = 5):
    #max 100 users can search i dont want a siutuation where a user can query 10,000 for example
    n = max(1, min(n, 100))
    return {"careers": career.top_careers(n, min_fights)}

FREE_PREDICTION_LIMIT = 10
@router.post("/api/predict")
def predict(db: DBDep, req: PredictRequest, user: User = Depends(get_curr_user)):
    """Predict a matchup. Returns win probabilities, styles, and the pick and fighhter advantages"""
    names = set(model.list_fighters())
    if req.fighter_a not in names or req.fighter_b not in names:
        raise HTTPException(status_code=404, detail="One or both fighters not found.")
    if req.fighter_a == req.fighter_b:
        raise HTTPException(status_code=400, detail="Pick two different fighters.")
    subscribed = user.subscription_status == "active"
    if not subscribed and user.free_predictions_used >= FREE_PREDICTION_LIMIT:
        raise HTTPException(
            status_code=402,
            detail="You've used your 10 free predictions — subscribe for unlimited.",
        )

    result = model.predict_fight_api(req.fighter_a, req.fighter_b)
    #only successful predictions
    _charge(db, user, subscribed, result)

    return result


def _charge(db, user, subscribed, result):
    """Burn one free prediction (or none, for subscribers) and stamp the count
    onto the response. Shared by /api/predict and /api/dream so the two can
    never drift apart on how the allowance is spent."""
    if subscribed:
        result["free_remaining"] = None                 # None = unlimited
    else:
        user.free_predictions_used += 1
        db.commit()
        result["free_remaining"] = FREE_PREDICTION_LIMIT - user.free_predictions_used


@router.get("/api/dream/fighters")
def dream_fighters():
    """Fighters with enough UFC fights to split into three career stages —
    a shorter list than /api/fighters, so the dream picker can't offer someone
    the model would then refuse."""
    return {"fighters": model.list_dream_fighters(), "stages": list(model.CAREER_STAGES)}


@router.post("/api/dream")
def dream(db: DBDep, req: DreamRequest, user: User = Depends(get_curr_user)):
    """Cross-era matchup: each fighter frozen at a career stage (Early/Prime/Late)
    rather than as they are today. Counts against the same free allowance as a
    normal prediction — it is the same model call."""
    names = set(model.list_dream_fighters())
    if req.fighter_a not in names or req.fighter_b not in names:
        raise HTTPException(
            status_code=404,
            detail="One or both fighters don't have enough UFC fights for career stages.",
        )
    if req.stage_a not in model.CAREER_STAGES or req.stage_b not in model.CAREER_STAGES:
        raise HTTPException(status_code=400, detail="Stage must be Early, Prime or Late.")
    # same fighter at two DIFFERENT stages is a legitimate matchup (prime vs late
    # Jones); the same stage twice is not a fight
    if req.fighter_a == req.fighter_b and req.stage_a == req.stage_b:
        raise HTTPException(status_code=400, detail="Pick two different fighters or two different stages.")

    subscribed = user.subscription_status == "active"
    if not subscribed and user.free_predictions_used >= FREE_PREDICTION_LIMIT:
        raise HTTPException(
            status_code=402,
            detail="You've used your 10 free predictions — subscribe for unlimited.",
        )

    result = model.dream_fight_api(req.fighter_a, req.stage_a, req.fighter_b, req.stage_b)
    if result is None:
        raise HTTPException(status_code=404, detail="Couldn't build a career stage for that matchup.")
    _charge(db, user, subscribed, result)

    return result
