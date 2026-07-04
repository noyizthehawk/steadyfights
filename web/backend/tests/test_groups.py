"""
Integration tests for the group create + join flow (routers/groups.py).

We call the endpoint FUNCTIONS directly (create_group / join_group), passing a
real in-memory DB session and a real User object in place of the Depends(...)
values. That exercises the actual endpoint logic — guards, the atomic pay+seat
transaction, error translation — without needing an HTTP server or auth cookie.

Runs against in-memory SQLite, so it never touches data/app.db.
Run:  .venv/bin/python -m web.backend.tests.test_groups
"""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import User, Group, GroupMember, CoinReason, CoinLedger, UFCFight, Pick
from ..ledgers import get_balance, record_movement
from ..routers.groups import create_group, join_group, group_leaderboard
from ..schemas import GroupCreate


def make_db():
    """Fresh in-memory DB + one user who already has 1000 coins to spend."""
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    user = User(email="tester@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    record_movement(db, user.id, 1000, CoinReason.purchase)   # give them coins
    return db, user


def a_group(entry_fee=300, days_ahead=7):
    """A valid GroupCreate body closing in the future."""
    return GroupCreate(name="High Rollers", entry_fee=entry_fee,
                       closes_at=datetime.utcnow() + timedelta(days=days_ahead))


def test_create_group():
    db, user = make_db()
    out = create_group(a_group(), db, user)
    assert out["id"] is not None
    assert out["owner_id"] == user.id
    assert out["entry_fee"] == 300


def test_join_deducts_and_seats():
    """The core of step 4: joining pays the fee AND creates the membership."""
    db, user = make_db()
    group = create_group(a_group(entry_fee=300), db, user)

    join_group(group["id"], db, user)

    # balance dropped by exactly the entry fee
    assert get_balance(db, user.id) == 700
    # a room_buyin ledger row exists, tagged with the group id
    row = db.query(CoinLedger).filter_by(reason=CoinReason.room_buyin).one()
    assert row.amount == -300
    assert row.reference_id == group["id"]
    # the membership exists and is active
    member = db.query(GroupMember).filter_by(
        group_id=group["id"], user_id=user.id).one()
    assert member.status == "active"


def test_cannot_join_twice():
    db, user = make_db()
    group = create_group(a_group(entry_fee=100), db, user)
    join_group(group["id"], db, user)

    try:
        join_group(group["id"], db, user)
        assert False, "second join should have been rejected"
    except HTTPException as e:
        assert e.status_code == 400
    # and they were only charged once
    assert get_balance(db, user.id) == 900


def test_insufficient_coins_rejected():
    db, user = make_db()                       # user has 1000
    group = create_group(a_group(entry_fee=5000), db, user)   # too pricey

    try:
        join_group(group["id"], db, user)
        assert False, "join should have been rejected for insufficient coins"
    except HTTPException as e:
        assert e.status_code == 400
    # nothing was charged, and no membership was created
    assert get_balance(db, user.id) == 1000
    assert db.query(GroupMember).count() == 0


def test_cannot_join_closed_room():
    db, user = make_db()
    # insert a Group directly with a past closes_at (create_group would reject it)
    closed = Group(name="Ended", owner_id=user.id, entry_fee=100,
                   closes_at=datetime.utcnow() - timedelta(days=1))
    db.add(closed)
    db.commit()
    db.refresh(closed)

    try:
        join_group(closed.id, db, user)
        assert False, "join should have been rejected for a closed room"
    except HTTPException as e:
        assert e.status_code == 400
    assert get_balance(db, user.id) == 1000    # untouched


def _add_user(db, email, coins=1000):
    u = User(email=email, hashed_password="x")
    db.add(u)
    db.commit()
    db.refresh(u)
    if coins:
        record_movement(db, u.id, coins, CoinReason.purchase)
    return u


def _seed_settled_fights(db, n=3, winner="A"):
    """n fights that are all settled with the same winner."""
    fights = []
    for i in range(n):
        f = UFCFight(matchup=f"m{i}", fighter_a="A", fighter_b="B", winner=winner)
        db.add(f)
        fights.append(f)
    db.commit()
    for f in fights:
        db.refresh(f)
    return fights


def test_room_leaderboard_scopes_to_members():
    """Step 5: the board shows ONLY the room's members, not the whole app."""
    db, owner = make_db()                       # owner already has 1000 coins
    alice = _add_user(db, "alice@x.com")
    bob = _add_user(db, "bob@x.com")            # will NOT join the room

    group = create_group(a_group(entry_fee=100), db, owner)
    join_group(group["id"], db, owner)
    join_group(group["id"], db, alice)

    fights = _seed_settled_fights(db, 3, winner="A")
    for f in fights:
        db.add(Pick(user_id=owner.id, fight_id=f.id, picked="A"))   # 3/3 correct
        db.add(Pick(user_id=alice.id, fight_id=f.id, picked="B"))   # 0/3 correct
        db.add(Pick(user_id=bob.id,   fight_id=f.id, picked="A"))   # correct but not a member
    db.commit()

    board = group_leaderboard(group["id"], db, owner)["leaderboard"]

    ids = {r["id"] for r in board}
    assert ids == {owner.id, alice.id}          # bob excluded — he's not in the room
    assert board[0]["id"] == owner.id           # higher winrate ranks first
    assert board[0]["winrate"] == 100.0
    assert board[-1]["id"] == alice.id


def test_non_member_cannot_view_board():
    db, owner = make_db()
    outsider = _add_user(db, "outsider@x.com")

    group = create_group(a_group(entry_fee=0), db, owner)   # free room
    join_group(group["id"], db, owner)

    try:
        group_leaderboard(group["id"], db, outsider)
        assert False, "outsider should not see a private room's board"
    except HTTPException as e:
        assert e.status_code == 403


if __name__ == "__main__":
    tests = [
        test_create_group,
        test_join_deducts_and_seats,
        test_cannot_join_twice,
        test_insufficient_coins_rejected,
        test_cannot_join_closed_room,
        test_room_leaderboard_scopes_to_members,
        test_non_member_cannot_view_board,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS   {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL   {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
