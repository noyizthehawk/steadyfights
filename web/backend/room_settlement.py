"""Room settlement: split a room's pot and pay out when it closes.

Lives outside routers/ on purpose. The weekly settle job (settle.py) runs as a
plain script in GitHub Actions, and it used to import run_settle_rooms from
routers/groups.py — which drags in dependencies.py and security.py, whose
import-time JWT_SECRET guard then killed a job that never signs a token.

Nothing here imports dependencies or security. Keep it that way: anything a cron
script needs belongs in a module whose imports a cron script can satisfy.
"""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from .ledgers import record_movement
from .models import CoinLedger, CoinReason, Group, GroupMember
from .stats import compute_leaderboard


def split_pot(pot: int, tie_groups: list): #tie group is a list of groups with user ids ranked from best to worst, ith tiesw
    #100% of post must me shared
    total_members = sum(len(members) for members in tie_groups)
    shares = [100] if total_members < 3 else [60,30,10]

    payouts = {}
    position = 0

    for group in tie_groups:
        if position >= len(shares):
            break  #ran out of paid slots

        group_pct = sum(shares[position:position + len(group)])
        group_amount = pot * group_pct // 100

        base, remainder = divmod(group_amount, len(group))
        for i, member in enumerate(group):
            payouts[member] = base + (1 if i < remainder else 0)

        position += len(group)

    leftover = pot - sum(payouts.values())
    if leftover and tie_groups:
        payouts[tie_groups[0][0]] += leftover

    return payouts

def settle_room(db: Session, group: Group):
    #if group is alredy settled, do nothing
    if group.settled_at is not None:
        return
    #if room is not closed yet do nothing
    if group.closes_at > datetime.utcnow():
        return
    member_ids = [m.user_id for m in db.query(GroupMember)
                  .filter_by(group_id=group.id, status="active")]

    staked = (db.query(func.coalesce(func.sum(CoinLedger.amount), 0))
              .filter(CoinLedger.reference_id == group.id,
                      CoinLedger.reason == CoinReason.room_buyin).scalar())
    pot = -staked
    # rank members by room points (10/correct pick, scoped to after they joined),
    # the SAME board the leaderboard endpoint shows — so paid winners == shown winners
    board = compute_leaderboard(db, user_ids=member_ids, min_settled=0,
                                group_id=group.id, rank_by="points")

    tie_groups = []
    prev = object()                             # sentinel so the first row starts a group
    for row in board: # for member in board
        if row["points"] == prev and tie_groups: # track the previous and compare to current
            tie_groups[-1].append(row["id"])    # same points -> tie
        else:
            tie_groups.append([row["id"]])
        prev = row["points"]
    found = {r["id"] for r in board}
    missing = [uid for uid in member_ids if uid not in found]
    if missing:
        tie_groups.append(missing)
    payouts = split_pot(pot, tie_groups)
    try:
        for user_id, amount in payouts.items():
            if amount > 0:
                record_movement(db, user_id, amount, CoinReason.room_payout,
                                reference_id=group.id, commit=False)
        group.settled_at = datetime.utcnow()    # stamp ALWAYS — even a 0 pot
        db.commit()
    except Exception:
        db.rollback()
        raise


def run_settle_rooms(db) -> dict:
    """Pay out every room whose close time has passed and that hasn't settled yet.
    Plain function so both a cron script and (optionally) an admin route can call it.

    ORDER MATTERS: run this AFTER fights are settled (run_settle), because rooms
    rank their members on SETTLED picks — settling rooms first would score everyone
    on still-unsettled fights.

    Each room settles in its own transaction, so one bad room can't block the
    others: a failure leaves that room's settled_at NULL and the next run retries
    it (safe, because settle_room is idempotent on settled_at)."""
    now = datetime.utcnow()
    due = (
        db.query(Group)
        .filter(Group.settled_at.is_(None), Group.closes_at <= now)
        .all()
    )
    settled = failed = 0
    for room in due:
        try:
            settle_room(db, room)
            settled += 1
        except Exception as e:                  # noqa: BLE001 — isolate per room
            failed += 1
            print(f"[settle_rooms] room {room.id} failed: {e}")
    return {"rooms": len(due), "settled": settled, "failed": failed}
