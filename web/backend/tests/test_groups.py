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
from ..models import (
    User, Group, GroupMember, CoinReason, CoinLedger, UFCFight, Pick, Friendship,
)
from ..ledgers import get_balance, record_movement
from ..routers.groups import (
    create_group, join_group, group_leaderboard,
    my_groups, group_detail, my_balance,
    browse_public_rooms, browse_private_rooms,
)
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


def a_group(entry_fee=300, days_ahead=7, is_public=False, name="High Rollers"):
    """A valid GroupCreate body closing in the future."""
    return GroupCreate(name=name, entry_fee=entry_fee, is_public=is_public,
                       closes_at=datetime.utcnow() + timedelta(days=days_ahead))


def _make_friends(db, a, b):
    """Create an accepted friendship between two users."""
    db.add(Friendship(requester_id=a.id, addressee_id=b.id, status="accepted"))
    db.commit()


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


def test_my_balance_reflects_ledger():
    db, user = make_db()                        # 1000 coins from a purchase
    assert my_balance(db, user)["balance"] == 1000

    group = create_group(a_group(entry_fee=300), db, user)
    join_group(group["id"], db, user)           # spend 300
    assert my_balance(db, user)["balance"] == 700


def test_my_groups_lists_only_my_rooms():
    db, owner = make_db()
    other = _add_user(db, "other@x.com")

    # owner is in A and B; C belongs to someone else and owner never joins it
    a = create_group(GroupCreate(name="A", entry_fee=0,
                                 closes_at=datetime.utcnow() + timedelta(days=1)), db, owner)
    b = create_group(GroupCreate(name="B", entry_fee=0,
                                 closes_at=datetime.utcnow() + timedelta(days=1)), db, owner)
    c = create_group(GroupCreate(name="C", entry_fee=0,
                                 closes_at=datetime.utcnow() + timedelta(days=1)), db, other)
    join_group(a["id"], db, owner)
    join_group(b["id"], db, owner)
    join_group(c["id"], db, other)              # owner is NOT in C

    out = my_groups(db, owner)["groups"]
    names = {g["name"] for g in out}
    assert names == {"A", "B"}                  # C excluded


def test_group_detail_pot_members_and_flags():
    db, owner = make_db()
    alice = _add_user(db, "alice2@x.com")
    outsider = _add_user(db, "outsider2@x.com")

    group = create_group(a_group(entry_fee=300), db, owner)
    join_group(group["id"], db, owner)          # pot += 300
    join_group(group["id"], db, alice)          # pot += 300

    # viewed by the owner
    detail = group_detail(group["id"], db, owner)
    assert detail["pot"] == 600                 # two 300-coin buy-ins
    assert detail["member_count"] == 2
    assert {m["id"] for m in detail["members"]} == {owner.id, alice.id}
    assert detail["is_owner"] is True
    assert detail["is_member"] is True
    assert detail["is_open"] is True

    # viewed by an outsider — visible, but flags are False
    outside_view = group_detail(group["id"], db, outsider)
    assert outside_view["is_owner"] is False
    assert outside_view["is_member"] is False
    assert outside_view["pot"] == 600           # pot is the same regardless of viewer


def test_pots_and_members_are_isolated_between_rooms():
    """Two rooms must not bleed into each other: each room's pot and member list
    reflects ONLY its own buy-ins. Guards the reference_id filter that step 6's
    payout depends on — if it broke, every pot would include everyone's coins."""
    db, owner = make_db()                        # 1000 coins
    alice = _add_user(db, "alice_iso@x.com")     # 1000
    bob = _add_user(db, "bob_iso@x.com")         # 1000

    room_a = create_group(a_group(entry_fee=100), db, owner)
    room_b = create_group(a_group(entry_fee=400), db, owner)

    # Room A: owner + alice  -> pot 200
    join_group(room_a["id"], db, owner)
    join_group(room_a["id"], db, alice)
    # Room B: owner + bob     -> pot 800
    join_group(room_b["id"], db, owner)
    join_group(room_b["id"], db, bob)

    detail_a = group_detail(room_a["id"], db, owner)
    detail_b = group_detail(room_b["id"], db, owner)

    # pots reflect ONLY their own room's buy-ins (not the other room's)
    assert detail_a["pot"] == 200
    assert detail_b["pot"] == 800

    # member lists don't bleed across rooms
    assert {m["id"] for m in detail_a["members"]} == {owner.id, alice.id}
    assert {m["id"] for m in detail_b["members"]} == {owner.id, bob.id}

    # and the leaderboard scopes per-room too (bob not in A's board, alice not in B's)
    board_a_ids = {r["id"] for r in group_leaderboard(room_a["id"], db, owner)["leaderboard"]}
    assert bob.id not in board_a_ids


def test_public_lobby_shows_only_open_public_rooms():
    """Public lobby: public + open only. Private rooms and closed rooms excluded."""
    db, owner = make_db()

    public_open = create_group(a_group(is_public=True, name="Open Public"), db, owner)
    create_group(a_group(is_public=False, name="A Private"), db, owner)   # private -> hidden
    # a closed public room (inserted directly; create_group rejects past closes_at)
    db.add(Group(name="Closed Public", owner_id=owner.id, entry_fee=0,
                 is_public=True, closes_at=datetime.utcnow() - timedelta(days=1)))
    db.commit()

    out = browse_public_rooms(db, owner)
    assert out["total"] == 1
    assert [r["id"] for r in out["rooms"]] == [public_open["id"]]


def test_private_lobby_shows_only_friends_private_rooms():
    """The leak guard: private rooms show ONLY if their owner is my friend.
    A stranger's private room must never appear."""
    db, me = make_db()
    friend = _add_user(db, "friend@x.com")
    stranger = _add_user(db, "stranger@x.com")
    _make_friends(db, me, friend)

    friend_private = create_group(a_group(is_public=False, name="Friend Private"), db, friend)
    create_group(a_group(is_public=True, name="Friend Public"), db, friend)     # public -> not here
    stranger_private = create_group(a_group(is_public=False, name="Stranger Private"), db, stranger)

    out = browse_private_rooms(db, me)
    ids = {r["id"] for r in out["rooms"]}
    assert ids == {friend_private["id"]}                 # only the friend's private room
    assert stranger_private["id"] not in ids             # stranger's room is NOT leaked


def test_private_lobby_empty_without_friends():
    db, me = make_db()
    lonely = _add_user(db, "lonely_owner@x.com")
    create_group(a_group(is_public=False, name="Nobody's Friend"), db, lonely)

    out = browse_private_rooms(db, me)                   # me has no friends
    assert out["rooms"] == []
    assert out["total"] == 0


def test_lobby_name_search_is_case_insensitive():
    db, owner = make_db()
    create_group(a_group(is_public=True, name="Alpha Room"), db, owner)
    create_group(a_group(is_public=True, name="Beta Room"), db, owner)

    out = browse_public_rooms(db, owner, q="alph")       # lowercase query, "Alpha" name
    assert [r["name"] for r in out["rooms"]] == ["Alpha Room"]
    assert out["total"] == 1


def test_lobby_pagination():
    db, owner = make_db()
    for i in range(22):                                  # 22 > PAGE_SIZE (20)
        create_group(a_group(is_public=True, name=f"Room {i:02d}"), db, owner)

    page1 = browse_public_rooms(db, owner, page=1)
    page2 = browse_public_rooms(db, owner, page=2)

    assert page1["total"] == 22 and page2["total"] == 22
    assert page1["page_size"] == 20
    assert len(page1["rooms"]) == 20                     # full first page
    assert len(page2["rooms"]) == 2                      # remainder
    # no overlap between pages
    assert not ({r["id"] for r in page1["rooms"]} & {r["id"] for r in page2["rooms"]})


if __name__ == "__main__":
    tests = [
        test_create_group,
        test_join_deducts_and_seats,
        test_cannot_join_twice,
        test_insufficient_coins_rejected,
        test_cannot_join_closed_room,
        test_room_leaderboard_scopes_to_members,
        test_non_member_cannot_view_board,
        test_my_balance_reflects_ledger,
        test_my_groups_lists_only_my_rooms,
        test_group_detail_pot_members_and_flags,
        test_pots_and_members_are_isolated_between_rooms,
        test_public_lobby_shows_only_open_public_rooms,
        test_private_lobby_shows_only_friends_private_rooms,
        test_private_lobby_empty_without_friends,
        test_lobby_name_search_is_case_insensitive,
        test_lobby_pagination,
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
