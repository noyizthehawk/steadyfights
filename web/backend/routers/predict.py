"""Fighter + prediction endpoints: list fighters, career summaries, top careers,
and the head-to-head prediction itself."""
from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_curr_user
from ..models import User
from ..schemas import PredictRequest
from part_2 import Prediction_model as model
from part_2 import career

router = APIRouter()


@router.get("/api/fighters")
def get_fighters():
    """List every fighter the model knows about this is used to fill the dropdowns
    """
    return {"fighters": model.list_fighters()}


@router.get("/api/fighters/{name}/career")
def fighter_career(name: str):
    """Career rundown for one fighter: phases, trajectory, and career score."""
    data = career.career_summary_api(name)
    if data is None:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return data


@router.get("/api/careers/top")
def top_careers_endpoint(n: int = 10, min_fights: int = 5):
    #max 100 users can search i dont want a siutuation where a user can query 10,000 for example
    n = max(1, min(n, 100))
    return {"careers": career.top_careers(n, min_fights)}


@router.post("/api/predict")
def predict(req: PredictRequest, user: User = Depends(get_curr_user)):
    """Predict a matchup. Returns win probabilities, styles, and the pick and fighhter advantages"""
    names = set(model.list_fighters())
    if req.fighter_a not in names or req.fighter_b not in names:
        raise HTTPException(status_code=404, detail="One or both fighters not found.")
    if req.fighter_a == req.fighter_b:
        raise HTTPException(status_code=400, detail="Pick two different fighters.")
    return model.predict_fight_api(req.fighter_a, req.fighter_b)
