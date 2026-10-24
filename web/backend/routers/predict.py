"""Fighter + prediction endpoints: list fighters, career summaries, top careers,
and the head-to-head prediction itself."""
import math
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_

from ..dependencies import get_curr_user, DBDep
from ..models import User, UFCFight, UFCEvent
from ..schemas import PredictRequest, DreamRequest
from .events import upcoming_events
from part_2 import Prediction_model as model
from part_2 import career
from .. import fighter_bio, headshots
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


# Every tale-of-the-tape stat competes for a card's one "best metric" bar.
# Each is ranked as a percentile against its own spread across the roster
# (career.stat_percentile, flipped where lower is better), so the winner is
# the thing this fighter is best at RELATIVE TO OTHER FIGHTERS — not whichever
# stat happens to run on bigger raw numbers (takedown defence always did).
_BEST_METRIC = {
    # key: (label, how to print the real figure)
    "str_acc": ("Striking accuracy", "{:.0f}%"),
    "str_def": ("Striking defence", "{:.0f}%"),
    "td_acc": ("Takedown accuracy", "{:.0f}%"),
    "td_def": ("Takedown defence", "{:.0f}%"),
    "slpm": ("Strikes landed / min", "{:.1f}"),
    "sapm": ("Strikes absorbed / min", "{:.1f}"),
    "td_avg": ("Takedowns / 15 min", "{:.1f}"),
    "sub_avg": ("Sub attempts / 15 min", "{:.1f}"),
}
# Below this many UFC fights the grappling stats are mostly noise: never being
# taken down in three fights reads as 100% defence, and one submission attempt
# in a short fight reads as an elite rate. Striking stats accumulate per minute
# and steady up much faster, so they stay eligible.
_GRAPPLING = {"td_acc", "td_def", "td_avg", "sub_avg"}
_GRAPPLING_MIN_FIGHTS = 5

TOP_CAREERS_SHOWN = 30   # the page shows one row and expands to all of these

# The fun lists under the GOATs, in page order. The numbers come from
# career.leaderboards(); the words live here. `label` heads each card's bar.
LEADERBOARDS = [
    {"key": "in_form", "title": "In form", "label": "Recent form",
     "meta": "best performances over the last 5 fights"},
    {"key": "gauntlet", "title": "The gauntlet", "label": "Opponent strength",
     "meta": "toughest last 5 opponents"},
    {"key": "leg_kicks", "title": "Leg kickers", "label": "Leg strikes thrown / min",
     "meta": "most leg strikes thrown per minute"},
    {"key": "clinch", "title": "Clinch merchants", "label": "Clinch strikes / 15 min",
     "meta": "most strikes landed in the clinch"},
    {"key": "tallest", "title": "Tallest", "label": "Height",
     "meta": "the biggest frames in the UFC"},
]


def _best_metric(name: str, total_fights: int) -> dict | None:
    """The stat this fighter is best at RELATIVE TO THE ROSTER, chosen by
    percentile: every stat's percentiles are spread evenly by definition, so
    none starts ahead (on the bar's own scale, a typical absorbed rate already
    sits at ~63/100 and would win too often)."""
    stats = career.get_fighter_stats(name) or {}
    candidates = []
    for key in _BEST_METRIC:
        value = stats.get(key)
        if value is None or (key in _GRAPPLING and total_fights < _GRAPPLING_MIN_FIGHTS):
            continue
        candidates.append((career.stat_percentile(key, float(value)), key, value))
    if not candidates:
        return None
    percentile, key, value = max(candidates)
    label, fmt = _BEST_METRIC[key]
    return {
        "key": key,
        "label": label,
        # the card draws the bar from `value` with the profile's own scaler
        # (lib/statScale), so fill and colour match the tale of the tape
        "value": float(value),
        "display": fmt.format(value),
        # "Top 4%" = better than 96% of fighters with 5+ UFC fights. Rounded
        # UP and floored at 1, so the very best read "Top 1%", never "Top 0%".
        "percentile": round(percentile, 1),
        "top_pct": max(1, math.ceil(100 - percentile)),
    }


def _fighter_card(name: str, pictures: dict) -> dict:
    """One fighter card. Debutants have no career data: their card keeps the
    name and picture with null numbers, which the UI renders as "UFC debut"
    rather than as zeros."""
    tag = career.fighter_tag(name)
    pic = pictures.get(normalize_name(name), {})
    base = {
        "name": name,
        "image_url": pic.get("image_url"),
        "image_credit": pic.get("credit"),
        # flags only exist for fighters on a scraped event card; legends: null
        "flag_url": pic.get("flag_url"),
        "country": pic.get("country"),
    }
    if tag is None:
        return {**base, "career_score": None, "record": None, "division": None,
                "overall_perf": None, "overall_opp": None, "recent_perf": None,
                "best_metric": None}
    return {
        **base,
        "career_score": tag["career_score"],
        "record": tag["record"],
        "division": tag["division"],
        "overall_perf": tag["overall_perf"],
        "overall_opp": tag["overall_opp"],
        "recent_perf": tag["recent_form"],       # same last-5 figure as the profile's recent ring
        "best_metric": _best_metric(name, tag["total_fights"]),
    }


def _card_fighters(event) -> list[str]:
    """Everyone on the card once, in bout order (main event first).

    The card churns all fight week: a withdrawal leaves the old bout in the
    table as "cancelled" (upserts never delete) next to the rebooked one, so a
    fighter can sit in two rows. Cancelled bouts are skipped, and if a fighter
    is still in two live bouts, only their NEWEST booking (highest id — the
    latest scrape to add it) counts."""
    live = [fight for fight in event.fights if fight.status != "cancelled"]
    newest = {}                                  # name_norm -> fight id
    for fight in sorted(live, key=lambda fight: fight.id, reverse=True):
        for name in (fight.fighter_a, fight.fighter_b):
            if name:
                newest.setdefault(normalize_name(name), fight.id)

    names, seen = [], set()
    for fight in live:                           # relationship order = bout order
        for name in (fight.fighter_a, fight.fighter_b):
            norm = normalize_name(name) if name else None
            if norm and newest[norm] == fight.id and norm not in seen:
                seen.add(norm)
                names.append(name)
    return names


@router.get("/api/fighters/browse")
def browse_fighters(db: DBDep):
    """The Fighters page's sections: everyone on the next card (in bout order)
    and the top careers. Pictures come from headshots.lookup, which only reads
    the database — the slow ufc.com / Commons fetching happens in the backfill
    script, never here."""
    # the same "next event" the events pages show
    upcoming = upcoming_events(db, int(time.time()))
    event = upcoming[0] if upcoming else None
    card_names = _card_fighters(event) if event else []
    top_names = [r["fighter"] for r in career.top_careers(n=TOP_CAREERS_SHOWN)]
    boards = career.leaderboards()
    board_names = [row["fighter"] for b in LEADERBOARDS for row in boards[b["key"]]]

    # one batch for every section
    pictures = headshots.lookup(db, card_names + top_names + board_names)
    return {
        "next_card": {
            "event": {"id": event.id, "title": event.title, "date": event.date,
                      "event_link": event.event_link},
            # the whole card in bout order; the page shows one row of it until
            # the user expands it
            "fighters": [_fighter_card(n, pictures) for n in card_names],
        } if event else None,
        "top_careers": [_fighter_card(n, pictures) for n in top_names],
        "leaderboards": [
            {**{k: b[k] for k in ("key", "title", "meta")},
             # each card carries the list's own stat (`highlight`), which the
             # card shows in place of the fighter's general best stat
             "fighters": [{**_fighter_card(row["fighter"], pictures),
                           "highlight": {"label": b["label"], **{k: row[k] for k in
                                         ("value", "display", "fill", "note")}}}
                          for row in boards[b["key"]]]}
            for b in LEADERBOARDS
        ],
    }


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


@router.get("/api/fighters/{name}/bio")
def fighter_bio_endpoint(name: str, db: DBDep):
    """LLM-written career rundown. Cached in Postgres against the fighter's
    fight count, so a given fighter is written about once per bout they take.
    """
    result = fighter_bio.get_or_create(db, name)
    if result.get("body") is None and result.get("reason") == "fighter not found":
        raise HTTPException(status_code=404, detail="Fighter not found")
    return result


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
