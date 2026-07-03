"""Tests for the ledgers module."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import User, CoinReason
from ..ledgers import get_balance, record_movement


def make_db():
    """Build a fresh, empty, in-memory DB and return (session, a valid user_id).

    'sqlite:///:memory:' lives entirely in RAM, so nothing is written to disk.
    create_all() builds every table from the models. We also insert one User so
    there's a real user_id to hang coins off of (user_id is a FK to users.id).
    """
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)          # build the tables in RAM
    TestSession = sessionmaker(bind=engine)
    db = TestSession()

    user = User(email="tester@example.com", hashed_password="x")  # stand-in user
    db.add(user)
    db.commit()
    db.refresh(user)                                # reload so user.id is filled in
    return db, user.id


# Each test follows the same shape: ARRANGE a world, ACT once, ASSERT the result.

def test_empty_balance_is_zero():
    """A user with no ledger rows has balance 0 — never None. (the get_balance fix)"""
    db, user_id = make_db()
    assert get_balance(db, user_id) == 0


def test_purchase_increases_balance():
    """A +500 purchase should make the balance 500."""
    db, user_id = make_db()
    record_movement(db, user_id, 500, CoinReason.purchase)
    assert get_balance(db, user_id) == 500


def test_spend_decreases_balance():
    """Buy 500, then spend 100 on a room buy-in -> balance should be 400."""
    db, user_id = make_db()
    record_movement(db, user_id, 500, CoinReason.purchase)
    record_movement(db, user_id, -100, CoinReason.room_buyin, reference_id=1)
    assert get_balance(db, user_id) == 400


def test_overdraw_is_rejected():
    """Spending more than you have must raise ValueError AND write no row."""
    db, user_id = make_db()
    record_movement(db, user_id, 500, CoinReason.purchase)

    raised = False
    try:
        record_movement(db, user_id, -9999, CoinReason.room_buyin)
    except ValueError:
        raised = True                               # good — the guard fired

    assert raised, "overdraw should have raised ValueError but didn't"
    # the failed spend must leave the balance untouched — nothing was written
    assert get_balance(db, user_id) == 500


# ---- plain-python runner, so you can run this without pytest installed ----
# pytest finds the test_* functions automatically. This block does the same by
# hand: call each test, print a PASS, or catch the failure and print why.
if __name__ == "__main__":
    tests = [
        test_empty_balance_is_zero,
        test_purchase_increases_balance,
        test_spend_decreases_balance,
        test_overdraw_is_rejected,
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
