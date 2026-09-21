"""Event comment endpoints: a one-level-deep discussion on each event page."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from ..dependencies import DBDep, get_curr_user, rate_limit_user, _utc
from ..models import User, UFCEvent, EventComment, CommentVote
from ..schemas import CommentCreate, CommentVoteRequest

router = APIRouter()


def _authors(db, comments) -> dict[int, dict]:
    """Display info for every author on the page in ONE query.

    The tempting version is `comment.user.username` while shaping, but that
    relationship lazy-loads, so a 20-comment page silently becomes 20 extra
    SELECTs. Same N+1 that `_room_summaries` in groups.py sidesteps.

    Selecting the three columns rather than whole User rows also means
    hashed_password can never reach a response by accident.
    """
    ids = {commenter.user_id for commenter in comments}
    if not ids:
        return {}
    rows = (
        db.query(User.id, User.username, User.avatar_url)
        .filter(User.id.in_(ids))
        .all()
    )
    return {uid: {"id": uid, "username": name, "avatar_url": avatar}
            for uid, name, avatar in rows}


def _vote_counts(db, comments) -> dict[int, dict]:
    """Likes and dislikes per comment, whole page in one query.

    Grouping by (comment_id, value) gives both tallies at once — a plain
    SUM(value) would only give the net, which can't render "5 up / 2 down".
    """
    ids = [c.id for c in comments]
    if not ids:
        return {}
    rows = (
        db.query(CommentVote.comment_id, CommentVote.value, func.count(CommentVote.id))
        .filter(CommentVote.comment_id.in_(ids))
        .group_by(CommentVote.comment_id, CommentVote.value)
        .all()
    )
    counts: dict[int, dict] = {}
    for comment_id, value, n in rows:
        bucket = counts.setdefault(comment_id, {"likes": 0, "dislikes": 0})
        bucket["likes" if value > 0 else "dislikes"] = n
    return counts


def _my_votes(db, comments, user_id: int) -> dict[int, int]:
    """What the viewer voted on each comment, so the UI can light up their own
    thumb. One query for the page."""
    ids = [c.id for c in comments]
    if not ids:
        return {}
    rows = (
        db.query(CommentVote.comment_id, CommentVote.value)
        .filter(CommentVote.comment_id.in_(ids), CommentVote.user_id == user_id)
        .all()
    )
    return {comment_id: value for comment_id, value in rows}


def _shape(comment, authors, counts, my_votes) -> dict:
    """
    Shape a single comment to the shape the UI expects.
    soft delete
    """
    gone = comment.deleted_at is not None
    tally = counts.get(comment.id, {"likes": 0, "dislikes": 0})
    return {
        "id": comment.id,
        "parent_id": comment.parent_id,
        "body": None if gone else comment.body,
        "deleted": gone,
        # Stamp UTC explicitly. The column is DateTime, not DateTime(timezone=
        # True), so the tzinfo set in the model default is dropped on write and
        # this comes back naive — which FastAPI then serializes with no offset.
        # JavaScript reads a bare date-time string as LOCAL time, so the browser
        # puts every comment hours into the future and "x ago" sticks at "just
        # now" forever.
        "created_at": _utc(comment.created_at),
        "user": None if gone else authors.get(comment.user_id),
        "likes": tally["likes"],
        "dislikes": tally["dislikes"],
        "my_vote": my_votes.get(comment.id, 0),
    }


@router.post(
    "/api/events/{event_id}/comments",
    status_code=201,
    dependencies=[Depends(rate_limit_user("comment_create", limit=10, window=60,
                                          detail="You're commenting too fast. Try again shortly."))],
)
def create_comment(event_id: int, comment: CommentCreate, db: DBDep, user: User = Depends(get_curr_user)):
    if db.get(UFCEvent, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    body = comment.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    parent_id = comment.parent_id
    if parent_id is not None:
        parent = db.get(EventComment, parent_id)
        if parent is None or parent.event_id != event_id:
            raise HTTPException(status_code=400, detail="Parent comment not found on this event")
        parent_id = parent.parent_id or parent.id

    new_comment = EventComment(
        event_id=event_id,
        user_id=user.id,
        parent_id=parent_id,
        body=body,
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)


    author = {new_comment.user_id: {"id": user.id, "username": user.username,
                                    "avatar_url": user.avatar_url}}
    return _shape(new_comment, author, {}, {})

@router.delete("/api/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int , db: DBDep, user: User = Depends(get_curr_user)):
    comment = db.get(EventComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    comment.deleted_at = datetime.now(timezone.utc)
    db.commit() 


@router.get("/api/events/{event_id}/comments")
def get_comments(
    event_id: int,
    db: DBDep,
    before_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_curr_user),
):
    """One page of top-level comments, newest first, each with its replies.

    Paging is by cursor (`before_id`), not OFFSET. Comments grow at the head, so
    with OFFSET a page 2 fetched after three new comments arrive re-serves rows
    already shown on page 1 and skips others — silently, no error.
    """
    event = db.get(UFCEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Top-level only. Replies come from the second query below, attached to
    # whichever parents land on this page.
    query = db.query(EventComment).filter(
        EventComment.event_id == event_id,
        EventComment.parent_id.is_(None),
    )
    if before_id is not None:
        query = query.filter(EventComment.id < before_id)
    tops = query.order_by(EventComment.id.desc()).limit(limit).all()

    replies = []
    if tops:
        replies = (
            db.query(EventComment)
            .filter(EventComment.parent_id.in_([t.id for t in tops]))
            .order_by(EventComment.id.asc())
            .all()
        )

    # Everything on the page, gathered once so the three lookups below are three
    # queries total rather than three per comment.
    page = list(tops) + list(replies)
    authors = _authors(db, page)
    counts = _vote_counts(db, page)
    my_votes = _my_votes(db, page, user.id)

    # Shape first, THEN nest — attaching raw ORM objects would hand FastAPI
    # something it can't serialize.
    shaped = {c.id: _shape(c, authors, counts, my_votes) for c in page}
    for top in tops:
        shaped[top.id]["replies"] = []
    for reply in replies:
        shaped[reply.parent_id]["replies"].append(shaped[reply.id])

    return {
        # Rebuilt from `tops`, not shaped.values() — that dict holds the replies
        # too and its order wouldn't match the sort.
        "comments": [shaped[t.id] for t in tops],
        # A full page probably means there's another. Cheaper than COUNT(*) on a
        # table being appended to while we read it.
        "has_more": len(tops) == limit,
        "next_before_id": tops[-1].id if tops else None,
    }


@router.get("/api/events/{event_id}/comments/since")
def comments_since(
    event_id: int,
    db: DBDep,
    since_id: int = Query(..., description="highest comment id the client already has"),
    limit: int = Query(100, ge=1, le=200),
    user: User = Depends(get_curr_user),
):
    """Everything newer than `since_id` — what the client polls.

    Deliberately NOT restricted to top-level rows. A reply added to a week-old
    comment is new content too, and a client watching only for new threads would
    never see it appear. Rows come back flat and the client slots each one into
    place by its parent_id, since it already has the parents rendered.

    Capped: a client that has been away for hours could otherwise ask for
    hundreds of rows in one go. When `has_more` is true the next poll picks up
    from the new `latest_id` — no cursor bookkeeping needed, because the
    client's "highest id seen" already IS the cursor.
    """
    if db.get(UFCEvent, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    rows = (
        db.query(EventComment)
        .filter(EventComment.event_id == event_id, EventComment.id > since_id)
        .order_by(EventComment.id.asc())
        .limit(limit)
        .all()
    )

    authors = _authors(db, rows)
    counts = _vote_counts(db, rows)
    my_votes = _my_votes(db, rows, user.id)

    return {
        "comments": [_shape(c, authors, counts, my_votes) for c in rows],
        "has_more": len(rows) == limit,
        # Echoed back so the client doesn't have to scan the array for the max.
        # Stays at since_id when nothing is new, which keeps polling idempotent.
        "latest_id": rows[-1].id if rows else since_id,
    }


@router.post("/api/comments/{comment_id}/vote")
def vote_comment(
    comment_id: int,
    vote: CommentVoteRequest,
    db: DBDep,
    user: User = Depends(get_curr_user),
):
    """
    Create or update a vote for a comment indempotently.
    """
    comment = db.get(EventComment, comment_id)
    #STANDARD CHECKS
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Cannot vote on a deleted comment")

    existing = (
        db.query(CommentVote)
        .filter(CommentVote.comment_id == comment_id, CommentVote.user_id == user.id)
        .first()
    )

    if vote.value == 0:
        #user is removing their vote
        if existing is not None: #the comment exists
            db.delete(existing)
    elif existing is not None:
        existing.value = vote.value    #update the vote now
    else:
        db.add(CommentVote(comment_id=comment_id, user_id=user.id, value=vote.value))

    try:
        db.commit()
    except IntegrityError:
        #incase 2 requests try to vote on the same comment at the same time
        db.rollback()
        existing = (
            db.query(CommentVote)
            .filter(CommentVote.comment_id == comment_id, CommentVote.user_id == user.id)
            .first()
        )
        if existing is not None:
            if vote.value == 0:
                db.delete(existing)
            else:
                existing.value = vote.value
            db.commit()

    tally = _vote_counts(db, [comment]).get(comment_id, {"likes": 0, "dislikes": 0})
    return {
        "id": comment_id,
        "likes": tally["likes"],
        "dislikes": tally["dislikes"],
        "my_vote": vote.value,
    }
