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
    browse_public_rooms, browse_private_rooms, split_pot, settle_room,
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
    assert detail["owner_name"] == "tester"      # for the "by ..." profile link
    assert detail["is_public"] is False          # a_group defaults to private

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


def test_private_lobby_shows_my_own_rooms():
    """The 'creator can't see their own room' fix: my own private rooms appear
    in my private lobby even if I have zero friends."""
    db, me = make_db()
    mine = create_group(a_group(is_public=False, name="My Secret Room"), db, me)

    out = browse_private_rooms(db, me)                   # me has no friends
    assert [r["id"] for r in out["rooms"]] == [mine["id"]]
    assert out["total"] == 1


def test_my_groups_includes_rooms_i_own_but_havent_joined():
    """Creating doesn't auto-join (the owner pays their buy-in like everyone
    else), but the room must still show in 'My rooms' so the owner can find it."""
    db, owner = make_db()
    created = create_group(a_group(name="Fresh Room"), db, owner)   # never joins

    out = my_groups(db, owner)["groups"]
    assert [g["id"] for g in out] == [created["id"]]


def test_lobby_tiles_show_owner_name_and_member_count():
    """Tapology-style tiles: each lobby room carries its owner's display name
    (email prefix) and a live count of active members."""
    db, owner = make_db()                        # tester@example.com -> "tester"
    alice = _add_user(db, "alice_tap@x.com")

    group = create_group(a_group(is_public=True, entry_fee=100, name="Tap Room"), db, owner)
    join_group(group["id"], db, owner)
    join_group(group["id"], db, alice)

    room = browse_public_rooms(db, owner)["rooms"][0]
    assert room["owner_name"] == "tester"
    assert room["member_count"] == 2

    # a brand-new room reports its creator and zero members
    fresh = create_group(a_group(is_public=True, name="Fresh"), db, alice)
    assert fresh["owner_name"] == "alice_tap"
    assert fresh["member_count"] == 0


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


# ---------- split_pot (pure payout math, no DB) ----------

def test_split_pot_clean_split():
    """Pot divides evenly: exact 60/30/10, unpaid 4th simply absent."""
    out = split_pot(1000, [["A"], ["B"], ["C"], ["D"]])
    assert out == {"A": 600, "B": 300, "C": 100}
    assert "D" not in out                       # absent = unpaid, no zero rows


def test_split_pot_remainder_goes_to_first():
    """The agreed acceptance case: pot 950, A+B tied for 1st.
    They pool 60+30=90% (855): 427 each + the divmod coin to A; then the
    global leftover coin also lands on A. Total paid == pot exactly."""
    out = split_pot(950, [["A", "B"], ["C"], ["D"]])
    assert out == {"A": 428, "B": 427, "C": 95}
    assert sum(out.values()) == 950


def test_split_pot_tie_straddles_paid_boundary():
    """A tie spanning paid and unpaid ranks pools only what the paid ranks
    earn: B,C,D tied for 2nd pool 30+10+0 = 40% and split it."""
    out = split_pot(1000, [["A"], ["B", "C", "D"]])
    assert out["A"] == 600
    assert out["B"] + out["C"] + out["D"] == 400
    assert max(out["B"], out["C"], out["D"]) - min(out["B"], out["C"], out["D"]) <= 1


def test_split_pot_small_rooms_winner_takes_all():
    """Under 3 members the shares collapse to [100]."""
    assert split_pot(500, [["A"]]) == {"A": 500}            # solo = own refund
    assert split_pot(500, [["A"], ["B"]]) == {"A": 500}     # 2nd of 2 gets nothing
    assert split_pot(500, [["A", "B"]]) == {"A": 250, "B": 250}  # 2-way tie splits


def test_split_pot_edge_cases():
    assert split_pot(300, []) == {}                          # empty room
    out = split_pot(0, [["A"], ["B"], ["C"]])                # free room, zero pot
    assert sum(out.values()) == 0


def test_split_pot_always_pays_exactly_the_pot():
    """Invariant sweep: for random pots and random tie-group shapes, payouts
    are non-negative and sum to EXACTLY the pot (no coins minted or lost)."""
    import random
    rng = random.Random(42)
    for _ in range(200):
        pot = rng.randrange(0, 100_000)
        n = rng.randrange(1, 9)                              # 1..8 members
        users, groups = list(range(n)), []
        while users:
            take = rng.randrange(1, len(users) + 1)
            groups.append(users[:take])
            users = users[take:]
        out = split_pot(pot, groups)
        assert all(v >= 0 for v in out.values()), (pot, groups, out)
        assert sum(out.values()) == pot, (pot, groups, out)


# ---------- settle_room (the payout engine, DB-backed) ----------

def _close(db, group_id):
    """Backdate a room's closes_at so settle_room will act on it.
    (create_group refuses a past closes_at, so we set it directly after members join.)"""
    g = db.get(Group, group_id)
    g.closes_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    return g


def _pick_record(db, user, fights, correct_n):
    """Give `user` picks on the fights: the first `correct_n` correct, rest wrong."""
    for i, f in enumerate(fights):
        db.add(Pick(user_id=user.id, fight_id=f.id,
                    picked="A" if i < correct_n else "B"))   # fights seeded winner="A"
    db.commit()


def test_settle_room_pays_top_three_and_stamps():
    db, owner = make_db()
    alice = _add_user(db, "alice_s@x.com")
    bob = _add_user(db, "bob_s@x.com")

    group = create_group(a_group(entry_fee=100), db, owner)
    for u in (owner, alice, bob):
        join_group(group["id"], db, u)                       # pot = 300, each now at 700

    fights = _seed_settled_fights(db, 3, winner="A")
    _pick_record(db, owner, fights, 3)                        # 100%
    _pick_record(db, alice, fights, 2)                        # 66.7%
    _pick_record(db, bob, fights, 0)                          # 0%

    g = _close(db, group["id"])
    settle_room(db, g)

    # each started at 1000, paid the 100 buy-in -> 900; then 60/30/10 of 300 = 180/90/30
    assert get_balance(db, owner.id) == 1080
    assert get_balance(db, alice.id) == 990
    assert get_balance(db, bob.id) == 930
    assert g.settled_at is not None
    # the pot was fully distributed, nothing minted or lost
    assert (1080 - 900) + (990 - 900) + (930 - 900) == 300


def test_settle_room_double_settle_is_noop():
    """The money-safety guard: settling an already-settled room pays nobody again."""
    db, owner = make_db()
    alice = _add_user(db, "alice_d@x.com")
    group = create_group(a_group(entry_fee=100), db, owner)
    join_group(group["id"], db, owner)
    join_group(group["id"], db, alice)
    fights = _seed_settled_fights(db, 3, winner="A")
    _pick_record(db, owner, fights, 3)
    _pick_record(db, alice, fights, 0)

    g = _close(db, group["id"])
    settle_room(db, g)
    bal_owner, bal_alice = get_balance(db, owner.id), get_balance(db, alice.id)
    payout_rows = db.query(CoinLedger).filter_by(reason=CoinReason.room_payout).count()

    settle_room(db, g)                                       # second run
    assert get_balance(db, owner.id) == bal_owner            # unchanged
    assert get_balance(db, alice.id) == bal_alice
    assert db.query(CoinLedger).filter_by(reason=CoinReason.room_payout).count() == payout_rows


def test_settle_room_open_room_is_noop():
    """A room that hasn't closed yet must not pay out."""
    db, owner = make_db()
    group = create_group(a_group(entry_fee=100), db, owner)
    join_group(group["id"], db, owner)
    g = db.get(Group, group["id"])                           # still open (future closes_at)

    settle_room(db, g)
    assert g.settled_at is None
    assert get_balance(db, owner.id) == 900                  # only the buy-in was taken


def test_settle_room_winner_takes_all_when_small():
    """Fewer than 3 members -> 1st takes the whole pot."""
    db, owner = make_db()
    alice = _add_user(db, "alice_w@x.com")
    group = create_group(a_group(entry_fee=100), db, owner)
    join_group(group["id"], db, owner)
    join_group(group["id"], db, alice)                       # pot = 200
    fights = _seed_settled_fights(db, 3, winner="A")
    _pick_record(db, owner, fights, 3)                       # 100%
    _pick_record(db, alice, fights, 1)                       # 33%

    g = _close(db, group["id"])
    settle_room(db, g)
    assert get_balance(db, owner.id) == 1100                 # 900 + whole 200 pot
    assert get_balance(db, alice.id) == 900                  # 2nd of 2 gets nothing


def test_settle_room_free_room_just_stamps():
    """A 0-coin room pays nobody but must still be marked settled."""
    db, owner = make_db()
    group = create_group(a_group(entry_fee=0), db, owner)
    join_group(group["id"], db, owner)                       # free -> no ledger movement
    g = _close(db, group["id"])

    settle_room(db, g)
    assert g.settled_at is not None
    assert get_balance(db, owner.id) == 1000                 # untouched
    assert db.query(CoinLedger).filter_by(reason=CoinReason.room_payout).count() == 0


def test_settle_room_member_with_no_picks_is_included_not_paid():
    """A member who never made a pick is dropped by the leaderboard's inner join;
    settle_room must still count them (ranked last) without crashing."""
    db, owner = make_db()
    alice = _add_user(db, "alice_np@x.com")
    bob = _add_user(db, "bob_np@x.com")
    carol = _add_user(db, "carol_np@x.com")                  # will make ZERO picks
    group = create_group(a_group(entry_fee=100), db, owner)
    for u in (owner, alice, bob, carol):
        join_group(group["id"], db, u)                       # pot = 400

    fights = _seed_settled_fights(db, 3, winner="A")
    _pick_record(db, owner, fights, 3)                       # 100%
    _pick_record(db, alice, fights, 2)                       # 66.7%
    _pick_record(db, bob, fights, 1)                         # 33%
    # carol: no picks at all

    g = _close(db, group["id"])
    settle_room(db, g)
    # each paid the 100 buy-in -> 900; 60/30/10 of 400 = 240/120/40; carol (4th) gets nothing
    assert get_balance(db, owner.id) == 1140                 # 900 + 240
    assert get_balance(db, alice.id) == 1020                 # 900 + 120
    assert get_balance(db, bob.id) == 940                    # 900 + 40
    assert get_balance(db, carol.id) == 900                  # paid nothing, buy-in only
    assert g.settled_at is not None


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
        test_private_lobby_shows_my_own_rooms,
        test_my_groups_includes_rooms_i_own_but_havent_joined,
        test_lobby_tiles_show_owner_name_and_member_count,
        test_lobby_name_search_is_case_insensitive,
        test_lobby_pagination,
        test_split_pot_clean_split,
        test_split_pot_remainder_goes_to_first,
        test_split_pot_tie_straddles_paid_boundary,
        test_split_pot_small_rooms_winner_takes_all,
        test_split_pot_edge_cases,
        test_split_pot_always_pays_exactly_the_pot,
        test_settle_room_pays_top_three_and_stamps,
        test_settle_room_double_settle_is_noop,
        test_settle_room_open_room_is_noop,
        test_settle_room_winner_takes_all_when_small,
        test_settle_room_free_room_just_stamps,
        test_settle_room_member_with_no_picks_is_included_not_paid,
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
