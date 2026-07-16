"""
Unit tests for the unified Stripe webhook (routers/coins.py: stripe_webhook).

Monkeypatches stripe.Webhook.construct_event so we can feed fake events without
real signatures, then asserts the DB side effects: subscription activate/cancel,
and that a coin purchase still credits (the coin path must survive the merge).

Runs against in-memory SQLite; never touches app.db.
Run:  .venv/bin/python -m web.backend.tests.test_billing
"""
import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import User
from ..ledgers import get_balance
from ..routers import coins as coins_module
from ..routers.coins import stripe_webhook


class FakeReq:
    """Minimal stand-in for a FastAPI Request — the webhook only calls .body()."""
    async def body(self):
        return b"{}"


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def add_user(db, email="s@x.com", customer_id=None):
    u = User(email=email, hashed_password="x", stripe_customer_id=customer_id)
    db.add(u); db.commit(); db.refresh(u)
    return u


def feed(event):
    # bypass signature verification: make construct_event return our fake event
    coins_module.stripe.Webhook.construct_event = lambda payload, sig, secret: event


def call_webhook(db):
    return asyncio.run(stripe_webhook(FakeReq(), db, "sig"))


def test_subscription_checkout_activates_user():
    db = make_db()
    user = add_user(db)
    feed({
        "type": "checkout.session.completed",
        "data": {"object": {"mode": "subscription", "id": "cs_sub_1",
                             "metadata": {"user_id": str(user.id)}}},
    })
    call_webhook(db)
    db.refresh(user)
    assert user.subscription_status == "active"


def test_subscription_deleted_cancels_user():
    db = make_db()
    user = add_user(db, customer_id="cus_123")
    user.subscription_status = "active"; db.commit()
    feed({
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_123"}},   # found by Customer id, not metadata
    })
    call_webhook(db)
    db.refresh(user)
    assert user.subscription_status == "canceled"


def test_coin_purchase_still_credits():
    """Regression: merging the webhook must not break the coin path."""
    db = make_db()
    user = add_user(db)
    feed({
        "type": "checkout.session.completed",
        "data": {"object": {"mode": "payment", "id": "cs_coin_1",
                             "metadata": {"user_id": str(user.id), "pack_id": "small"}}},
    })
    call_webhook(db)
    assert get_balance(db, user.id) == 1000   # small pack = 1000 coins


def test_coin_purchase_is_idempotent():
    db = make_db()
    user = add_user(db)
    feed({
        "type": "checkout.session.completed",
        "data": {"object": {"mode": "payment", "id": "cs_dupe",
                             "metadata": {"user_id": str(user.id), "pack_id": "small"}}},
    })
    call_webhook(db)
    call_webhook(db)                          # same session id delivered twice
    assert get_balance(db, user.id) == 1000   # credited once, not twice


if __name__ == "__main__":
    tests = [
        test_subscription_checkout_activates_user,
        test_subscription_deleted_cancels_user,
        test_coin_purchase_still_credits,
        test_coin_purchase_is_idempotent,
    ]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS   {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL   {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
