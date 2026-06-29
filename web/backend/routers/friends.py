"""Friends endpoints: invite, accept, decline, list friends and pending invites."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, or_

from ..dependencies import DBDep, get_curr_user
from ..models import User, Friendship
from ..schemas import InviteRequest

router = APIRouter()


@router.post("/api/friends/invite")
def send_invite(req: InviteRequest, db: DBDep, user: User = Depends(get_curr_user)):
    """Invite another user (by email or user_id) to be friends -> a 'pending' row."""
    if req.user_id is not None:
        target = db.get(User, req.user_id)
    elif req.email:
        target = db.execute(select(User).where(User.email == req.email)).scalar_one_or_none()
    else:
        raise HTTPException(status_code=400, detail="Provide an email or user_id")
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="You can't invite yourself")

    # relation in either direction
    existing = db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == user.id, Friendship.addressee_id == target.id),
                and_(Friendship.requester_id == target.id, Friendship.addressee_id == user.id),
            )
        )
    ).scalar_one_or_none()

    if existing:
        # if THEY already invited ME, accepting is the right move imo
        if existing.status == "pending" and existing.addressee_id == user.id:
            existing.status = "accepted"
            db.commit()
            return {"status": "accepted", "friendship_id": existing.id}
        raise HTTPException(status_code=400, detail="Already invited or already friends")

    invite = Friendship(requester_id=user.id, addressee_id=target.id, status="pending")
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {"status": "pending", "invite_id": invite.id}


@router.post("/api/friends/{id}/accept")
def accept_invite(id: int, db: DBDep, user: User = Depends(get_curr_user)):
    """Accept a pending invite addressed to me  flip status to 'accepted'."""
    invite = db.get(Friendship, id)
    # only the recipient of a still-pending invite may accept it
    if invite is None or invite.addressee_id != user.id or invite.status != "pending":
        raise HTTPException(status_code=404, detail="Invite not found")
    invite.status = "accepted"
    db.commit()
    return {"status": "accepted", "friendship_id": invite.id}


@router.post("/api/friends/{id}/decline")
def decline_invite(id: int, db: DBDep, user: User = Depends(get_curr_user)):
    """Decline a pending invite addressed to me justdelete the row."""

    invite = db.get(Friendship, id) # get friendship table from db
    #if that inv doesnt exist or user inv himself or invite not pending
    if invite is None or invite.addressee_id != user.id or invite.status != "pending":
        raise HTTPException(status_code=404, detail="Invite not found")
    db.delete(invite)
    db.commit()
    return {"status": "declined"}


@router.get("/api/friends")
def get_friends(db: DBDep, user: User = Depends(get_curr_user)):
    """All my friends (accepted invites)."""
    # get all accepted friendships for a user
    rows = db.execute(
        select(Friendship).where(
            Friendship.status == "accepted",
            or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
        )
    ).scalars().all()

    friends = []
    for f in rows:
        other_id = f.addressee_id if f.requester_id == user.id else f.requester_id
        other = db.get(User, other_id)
        if other:
            friends.append({"id": other.id, "email": other.email})
    return {"friends": friends} #return dictionary


@router.get("/api/friends/pending")
def get_pending(db: DBDep, user: User = Depends(get_curr_user)):
    """Invites waiting for ME to answer (I'm the addressee). Returns who sent each."""
    rows = db.execute(
        select(Friendship).where(
            Friendship.addressee_id == user.id,
            Friendship.status == "pending",
        )
    ).scalars().all()

    pending = []
    for f in rows:
        requester = db.get(User, f.requester_id)
        if requester:
            pending.append({"invite_id": f.id, "from": requester.email})
    return {"pending": pending}
