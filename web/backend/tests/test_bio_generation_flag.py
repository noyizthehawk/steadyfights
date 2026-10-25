"""With BIO_GENERATION off (the local default), a profile never pays for a bio:
cached text is served, a missing one stays missing, Sonnet is never called.

Run:  .venv/bin/python -m pytest web/backend/tests/test_bio_generation_flag.py
"""
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import FighterBio
from .. import fighter_bio

SUMMARY = {"fighter": "Jon Jones", "total_fights": 22}


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _get(db, enabled):
    with patch.object(fighter_bio, "BIO_GENERATION_ENABLED", enabled), \
         patch.object(fighter_bio, "career_summary_api", return_value=SUMMARY), \
         patch.object(fighter_bio, "is_configured", return_value=True), \
         patch.object(fighter_bio, "_generation_budget_left", return_value=True), \
         patch.object(fighter_bio, "generate", return_value="fresh bio") as gen:
        return fighter_bio.get_or_create(db, "Jon Jones"), gen


def test_off_never_generates_and_serves_nothing_when_uncached():
    out, gen = _get(make_db(), enabled=False)
    assert out["body"] is None and not gen.called


def test_off_still_serves_a_cached_bio_even_if_stale():
    db = make_db()
    db.add(FighterBio(fighter_norm="jon jones", fighter="Jon Jones", body="old bio",
                      fights_at_generation=21, model="x"))
    db.commit()
    out, gen = _get(db, enabled=False)
    assert out["body"] == "old bio" and not gen.called


def test_on_generates_as_before():
    out, gen = _get(make_db(), enabled=True)
    assert out["body"] == "fresh bio" and gen.called
