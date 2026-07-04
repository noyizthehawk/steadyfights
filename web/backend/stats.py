"""shared stats functions, imported by the routers"""
from sqlalchemy import func, case, and_

from .models import User, UFCFight, Pick


def compute_user_stats(db, user_id, event_id=None):
    """A user's pick stats, optionally narrowed to one event. Returns the summary
    numbers PLUS the per-fight breakdown.
      ---- the stats endpoint uses the whole thing
      ---- the profile uses just the overall summary (event_id=None)
    """
    q = (
        db.query(UFCFight, Pick.picked)
        .join(Pick, and_(Pick.fight_id == UFCFight.id, Pick.user_id == user_id))
    )
    # only narrow to one event when the caller asks for it; otherwise it's overall
    if event_id is not None:
        q = q.filter(UFCFight.event_id == event_id)

    rows = q.all()

    fights = []
    correct = settled = 0 # starts at 0
    for fight, picked in rows:
        is_settled = fight.winner is not None
        is_correct = is_settled and picked == fight.winner
        if is_settled:
            settled += 1 #number of settled picks
            correct += is_correct 
        fights.append({
            "event_id": fight.event_id,
            "matchup": fight.matchup,
            "fighter_a": fight.fighter_a,
            "fighter_b": fight.fighter_b,
            "img_a": fight.img_a,
            "img_b": fight.img_b,
            "picked": picked,
            "winner": fight.winner,
            "correct": is_correct,
        })

    return {
        "user_id": user_id,
        "event_id": event_id,
        "picks_made": len(fights),
        "fights_settled": settled,
        "correct": correct,
        "winrate": round(correct / settled * 100, 1) if settled else None,
        "fights": fights,
    }


def compute_leaderboard(db, user_ids=None, min_settled=3):
    """The leaderboard is a list of users with pick stats, ranked by winrate.

    Global board: call with no args (all users, >= 3 settled picks).
    Room board:   pass user_ids=[member ids] to score only that room's members,
                  and usually a lower min_settled (a small room can't clear 3).
    """
    q = (
        db.query(
            User.id,                                             # so cards can identify the user
            User.email,                                          # user email
            func.count(Pick.id).label("total_picks"),            # all picks
            func.count(UFCFight.winner).label("settled"),        # non-null winners = settled
            # when picked == winner it's a correct pick, else 0
            func.sum(case((Pick.picked == UFCFight.winner, 1), else_=0)).label("correct"),
        )
        .join(Pick, Pick.user_id == User.id)
        .join(UFCFight, Pick.fight_id == UFCFight.id)            # inner join fights on picks
    )
    # room-scoped boards narrow to the given members; the global board passes nothing
    if user_ids is not None:
        q = q.filter(User.id.in_(user_ids))

    rows = (
        q.group_by(User.id)
        .having(func.count(UFCFight.winner) >= min_settled)     # min settled picks to qualify
        .all()
    )

    board = []
    for uid, email, total, settled, correct in rows:
        correct = correct or 0
        winrate = round(correct / settled * 100, 1) if settled else None
        board.append({
            "id": uid,                       # used to send a friend invite from a card
            "name": email.split("@")[0],     # local part only — don't expose the full email
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
    return board
