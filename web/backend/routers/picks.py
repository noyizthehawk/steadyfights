"""Pick endpoints: make/update a pick, list my picks, and my overall winrate."""
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..dependencies import DBDep, get_curr_user
from ..models import User, UFCFight, Pick
from ..schemas import PickRequest

router = APIRouter()


@router.post("/api/picks")
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


@router.get("/api/picks/me")
def my_picks(db: DBDep, user: User = Depends(get_curr_user)):
    """The logged-in user's picks, keyed by fight_id — used to pre-fill the buttons."""
    picks = db.execute(select(Pick).where(Pick.user_id == user.id)).scalars().all()
    return {"picks": {p.fight_id: p.picked for p in picks}}


@router.get("/api/picks/me/stats")
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
