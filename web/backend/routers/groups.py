from ..models import  CoinReason, Group, GroupMember, User
from fastapi import APIRouter, Depends, HTTPException
from ..schemas import GroupCreate
from ..ledgers import record_movement
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
                  entry_fee=body.entry_fee, closes_at=closes)
    db.add(group)
    db.commit()
    db.refresh(group)      # reload so group.id is populated

    return {"id": group.id, "name": group.name, "entry_fee": group.entry_fee,
            "owner_id": group.owner_id, "closes_at": group.closes_at}


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

