from ..models import  CoinReason, Group, GroupMember, User, CoinLedger, Friendship
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from ..schemas import GroupCreate
from ..ledgers import record_movement, get_balance
from ..stats import compute_leaderboard
from ..dependencies import get_curr_user, DBDep
from datetime import datetime, timezone

router = APIRouter()

@router.post("/api/groups/{group_id}/join")
def join_group(group_id: int, db: DBDep, user: User = Depends(get_curr_user)):
    #The room must exist
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    #the room should still be open 
    if group.closes_at <= datetime.utcnow():
        raise HTTPException(400, "This room is closed")
    
    #if a user is already in this room
    already = db.query(GroupMember).filter_by(
        group_id=group_id, user_id=user.id).first()
    if already:
        raise HTTPException(400, "You are already in this room")
    
    #pay and sit
    try: 
        if group.entry_fee > 0:
            record_movement(db, user.id, -group.entry_fee,
                            CoinReason.room_buyin, reference_id=group_id,
                            commit=False)                      # no commit yet
        db.add(GroupMember(group_id=group_id, user_id=user.id, status="active"))
        db.commit()
    except ValueError:
        db.rollback()
        raise HTTPException(400, "You don't have enough coins")
    return {"status": "joined", "group_id": group_id}


@router.post("/api/groups")
def create_group(body: GroupCreate, db: DBDep, user: User = Depends(get_curr_user)):
    # --- validate ---
    if not body.name.strip():
        raise HTTPException(400, "Name is required")
    if body.entry_fee < 0:
        raise HTTPException(400, "Entry fee cannot be negative")
    
    #closes at must be in the future
    closes = body.closes_at
    if closes.tzinfo is not None:
        closes = closes.astimezone(timezone.utc).replace(tzinfo=None)
    if closes <= datetime.utcnow():
        raise HTTPException(400, "closes_at must be in the future")
    
    # create
    group = Group(name=body.name.strip(), owner_id=user.id,
                  entry_fee=body.entry_fee, closes_at=closes,
                  is_public=body.is_public)
    db.add(group)
    db.commit()
    db.refresh(group)      # reload so group.id is populated

    #same shape as the lobby tiles; a brand-new room has no members yet
    return {"id": group.id, "name": group.name, "entry_fee": group.entry_fee,
            "owner_id": group.owner_id, "closes_at": group.closes_at,
            "is_public": group.is_public,
            "owner_name": user.email.split("@")[0], "member_count": 0}


@router.get("/api/groups/{group_id}/leaderboard")
def group_leaderboard(group_id: int, db: DBDep, user: User = Depends(get_curr_user)):
    #the room must exist
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")

    #active members of this room
    member_ids = [m.user_id for m in db.query(GroupMember).filter_by(
        group_id=group_id, status="active").all()]

    #a private paid room's board is only for its members (owner counts too)
    if user.id != group.owner_id and user.id not in member_ids:
        raise HTTPException(403, "You are not in this room")

    #no members yet -> empty board (also avoids an empty IN () query)
    if not member_ids:
        return {"group_id": group_id, "leaderboard": []}

    #score ONLY this room's members; min_settled=0 so everyone playing shows up
    board = compute_leaderboard(db, user_ids=member_ids, min_settled=0)
    return {"group_id": group_id, "leaderboard": board}
@router.get("/api/coins/balance")
def my_balance(db: DBDep, user: User = Depends(get_curr_user)):
    balance = get_balance(db, user.id)
    return {"balance": balance}

#get list of groups for a user
@router.get("/api/groups")
def my_groups(db: DBDep, user: User = Depends(get_curr_user)):
    #groups I'm an active member of
    member_group_ids = [
        gid for (gid,) in db.query(GroupMember.group_id)
        .filter(GroupMember.user_id == user.id,
                GroupMember.status == "active")
    ]
    #"my rooms" = rooms I'm in OR rooms I own — creating doesn't auto-join
    #(the owner pays their buy-in like everyone else), so without the owner_id
    #check a freshly created room would appear in no tab at all
    groups = db.query(Group).filter(
        or_(Group.owner_id == user.id, Group.id.in_(member_group_ids))
    ).all()
    return {"groups": _room_summaries(db, groups)}
    
    
@router.get("/api/groups/{group_id}")
def group_detail(group_id: int, db: DBDep, user: User = Depends(get_curr_user)):
    #the room must exist
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")

    #active members, joined to users so we can show names (not full emails)
    rows = (
        db.query(User.id, User.email)
        .join(GroupMember, GroupMember.user_id == User.id)
        .filter(GroupMember.group_id == group_id,
                GroupMember.status == "active")
        .all()
    )
    members = [{"id": uid, "name": email.split("@")[0]} for uid, email in rows]
    member_ids = {uid for uid, _ in rows}

    #pot = coins staked in this room. buy-ins are stored NEGATIVE, so negate the sum.
    staked = (
        db.query(func.coalesce(func.sum(CoinLedger.amount), 0))
        .filter(CoinLedger.reference_id == group_id,
                CoinLedger.reason == CoinReason.room_buyin)
        .scalar()
    )
    pot = -staked

    #owner display name for the "by ..." link (owner may not be a member yet)
    owner = db.get(User, group.owner_id)
    owner_name = owner.email.split("@")[0] if owner else "unknown"

    return {
        "id": group.id,
        "name": group.name,
        "entry_fee": group.entry_fee,
        "closes_at": group.closes_at,
        "owner_id": group.owner_id,
        "owner_name": owner_name,
        "is_public": group.is_public,
        "is_open": group.closes_at > datetime.utcnow(),
        "pot": pot,
        "member_count": len(members),
        "members": members,
        # handy flags so the UI knows what buttons to show this viewer
        "is_member": user.id in member_ids,
        "is_owner": user.id == group.owner_id,
    }


PAGE_SIZE = 20


def _room_summaries(db, rooms: list) -> list[dict]:
    """Compact room shapes for the lobby tiles. Owner names and live member
    counts are fetched in TWO batched queries for the whole page — not one
    pair of queries per room (the classic N+1 trap)."""
    if not rooms:
        return []

    #owner display names, same rule as group_detail: the part before the @
    owner_rows = db.query(User.id, User.email).filter(
        User.id.in_({r.owner_id for r in rooms})).all()
    owner_names = {uid: email.split("@")[0] for uid, email in owner_rows}

    #active-member counts, grouped per room in one query
    count_rows = (
        db.query(GroupMember.group_id, func.count(GroupMember.id))
        .filter(GroupMember.group_id.in_([r.id for r in rooms]),
                GroupMember.status == "active")
        .group_by(GroupMember.group_id)
        .all()
    )
    counts = dict(count_rows)

    return [{
        "id": g.id,
        "name": g.name,
        "entry_fee": g.entry_fee,
        "closes_at": g.closes_at,
        "is_public": g.is_public,
        "owner_id": g.owner_id,
        "owner_name": owner_names.get(g.owner_id, "unknown"),
        "member_count": counts.get(g.id, 0),
    } for g in rooms]


def _paginate(db, query, page: int) -> dict:
    """Shared paging: total count + one page of rooms (soonest-closing first)."""
    page = max(1, page)
    total = query.count()
    rooms = (
        query.order_by(Group.closes_at.asc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    return {"rooms": _room_summaries(db, rooms),
            "total": total, "page": page, "page_size": PAGE_SIZE}


@router.get("/api/rooms/public")
def browse_public_rooms(db: DBDep, user: User = Depends(get_curr_user),
                        q: str = "", page: int = 1):
    """Public lobby — every public room that's still open. Optional name search."""
    query = db.query(Group).filter(
        Group.is_public.is_(True),
        Group.closes_at > datetime.utcnow(),        # only joinable (open) rooms
    )
    if q:
        query = query.filter(Group.name.ilike(f"%{q}%"))   # LIKE is case-insensitive on SQLite
    return _paginate(db, query, page)


@router.get("/api/rooms/private")
def browse_private_rooms(db: DBDep, user: User = Depends(get_curr_user),
                         q: str = "", page: int = 1):
    """Private lobby — private rooms owned by my friends or by me (open ones only)."""
    # my accepted friendships (either direction) -> the friend is the OTHER side
    friendships = db.query(Friendship).filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == user.id,
            Friendship.addressee_id == user.id),
    ).all()
    friend_ids = [f.addressee_id if f.requester_id == user.id else f.requester_id
                  for f in friendships]
    # rooms owned by my friends OR by me — I can always see my own private rooms
    visible_owner_ids = friend_ids + [user.id]

    query = db.query(Group).filter(
        Group.is_public.is_(False),
        Group.owner_id.in_(visible_owner_ids),
        Group.closes_at > datetime.utcnow(),
    )
    if q:
        query = query.filter(Group.name.ilike(f"%{q}%"))
    return _paginate(db, query, page)

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

def settle_room(db: DBDep, group: Group):
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
    board = compute_leaderboard(db, user_ids=member_ids, min_settled=0)
    
    
    tie_groups = []
    prev = object()                             # sentinel so the first row starts a group
    for row in board:
        if row["winrate"] == prev and tie_groups:
            tie_groups[-1].append(row["id"])    # same winrate -> tie
        else:
            tie_groups.append([row["id"]])
        prev = row["winrate"]
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



   
    


       
   

    

    
    
   

