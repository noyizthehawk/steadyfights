"""
Unit tests for the freemium gate on POST /api/predict (routers/predict.py).

Calls the endpoint FUNCTION directly with an in-memory DB + a real User, and
monkeypatches the model so no training run happens — we're testing the 10-free
gate, not the prediction math. Runs against in-memory SQLite; never touches app.db.

Run:  .venv/bin/python -m web.backend.tests.test_predict
"""
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import User
from ..routers import predict as predict_module
from ..routers.predict import predict, FREE_PREDICTION_LIMIT
from ..schemas import PredictRequest

FIGHTERS = ["Fighter A", "Fighter B"]


def patch_model():
    # swap the real model for fakes ONCE: known fighters + a dummy result, so
    # calling predict() never triggers a real train()/predict_fight_api
    predict_module.model.list_fighters = lambda: FIGHTERS
    predict_module.model.predict_fight_api = lambda a, b: {"pick": a, "prob_a": 60.0, "prob_b": 40.0}


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def a_user(db, subscribed=False):
    u = User(email="p@x.com", hashed_password="x",
             subscription_status="active" if subscribed else None)
    db.add(u); db.commit(); db.refresh(u)
    return u


def a_req():
    return PredictRequest(fighter_a="Fighter A", fighter_b="Fighter B")


def test_free_predictions_count_down_then_402():
    db = make_db()
    user = a_user(db)
    # the first 10 succeed and report the remaining allowance counting down
    for i in range(FREE_PREDICTION_LIMIT):
        out = predict(db, a_req(), user)
        assert out["free_remaining"] == FREE_PREDICTION_LIMIT - (i + 1)
    assert user.free_predictions_used == 10
    # the 11th is blocked with a 402
    try:
        predict(db, a_req(), user)
        assert False, "11th prediction should have been blocked"
    except HTTPException as e:
        assert e.status_code == 402


def test_failed_prediction_does_not_burn_allowance():
    db = make_db()
    user = a_user(db)
    # unknown fighter -> 404 BEFORE the counter is touched
    bad = PredictRequest(fighter_a="Nobody", fighter_b="Fighter B")
    try:
        predict(db, bad, user)
        assert False, "unknown fighter should 404"
    except HTTPException as e:
        assert e.status_code == 404
    assert user.free_predictions_used == 0     # allowance untouched


def test_subscriber_is_unlimited_and_uncounted():
    db = make_db()
    user = a_user(db, subscribed=True)
    for _ in range(FREE_PREDICTION_LIMIT + 5):     # well past the free limit
        out = predict(db, a_req(), user)
        assert out["free_remaining"] is None       # None = unlimited
    assert user.free_predictions_used == 0         # subscribers never consume free picks


if __name__ == "__main__":
    patch_model()
    tests = [
        test_free_predictions_count_down_then_402,
        test_failed_prediction_does_not_burn_allowance,
        test_subscriber_is_unlimited_and_uncounted,
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
