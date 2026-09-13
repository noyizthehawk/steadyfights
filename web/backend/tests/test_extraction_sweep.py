"""Tests for run_extraction_sweep's skip logic.

The sweep used to skip a (pundit, event) pair whenever a NotableExtraction row
existed, whatever video that row pointed at. That made the first successful
match permanent: pundits post their real full-card video late in fight week, so
a row written early in the week — off a teaser, a rant, or by a matcher since
fixed — stood forever, and re-running the sweep could not replace it. The only
way back in was `reextract=True`, which redoes every pair and burns the Gemini
free tier (20 requests/day) on pairs that were already correct.

The sweep now re-matches before skipping, and only spends an extraction when the
best-scoring video has actually changed.

Run:  .venv/bin/python -m pytest web/backend/tests/test_extraction_sweep.py
"""
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import UFCEvent, UFCFight, User, NotableExtraction
from .. import predictions_ai
from ..predictions_ai import run_extraction_sweep

DAY = 86400


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def make_event(db, days_out=7):
    event = UFCEvent(title="Van vs Pantoja 2", event_link="/event/cryptocom-ufc-331",
                     date=int(time.time()) + days_out * DAY, venue="Crypto.com Arena")
    db.add(event)
    db.flush()
    db.add(UFCFight(event_id=event.id, matchup="Joshua Van vs Alexandre Pantoja",
                    fighter_a="Joshua Van", fighter_b="Alexandre Pantoja"))
    db.commit()
    db.refresh(event)
    return event


def make_pundit(db, username="LucasTracyMMA"):
    user = User(email=f"{username}@example.com", username=username,
                hashed_password="x", is_notable=True,
                youtube_channel_id="UC7LzaJA-R2E52qzd5GW-kpg")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def stub(monkeypatch, *, matches, extractions):
    """Point the sweep at a fixed match result, and record what it extracts.

    `matches` is the video find_prediction_video returns (None for no match);
    `extractions` is the list each run_extraction call appends its video_id to.
    """
    monkeypatch.setattr(predictions_ai, "find_prediction_video",
                        lambda channel_id, event: matches)

    def fake_run_extraction(db, user, event, video_id=None):
        extractions.append(video_id)
        return {"ok": True, "video_id": video_id, "created": 1, "updated": 0}

    monkeypatch.setattr(predictions_ai, "run_extraction", fake_run_extraction)


def test_a_newer_better_match_replaces_a_stale_row(monkeypatch):
    """The prod bug: a pundit's full-card video lands after an early match was
    already stored, and the sweep has to pick it up without being forced."""
    db = make_db()
    event = make_event(db)
    user = make_pundit(db)
    db.add(NotableExtraction(user_id=user.id, event_id=event.id, video_id="OLD_RANT"))
    db.commit()

    done = []
    stub(monkeypatch, matches={"video_id": "NEW_FULLCARD"}, extractions=done)
    result = run_extraction_sweep(db)

    assert done == ["NEW_FULLCARD"], "the newly-matched video should be extracted"
    assert result["extracted"] == 1
    assert result["skipped"] == 0
    assert result["details"][0]["replaced_stale_match"] is True


def test_an_unchanged_match_is_skipped_without_spending_an_extraction(monkeypatch):
    """The quota guard: re-matching is cheap, extracting is not. A row that is
    still the best match must not be re-transcribed on every sweep."""
    db = make_db()
    event = make_event(db)
    user = make_pundit(db)
    db.add(NotableExtraction(user_id=user.id, event_id=event.id, video_id="SAME"))
    db.commit()

    done = []
    stub(monkeypatch, matches={"video_id": "SAME"}, extractions=done)
    result = run_extraction_sweep(db)

    assert done == [], "no extraction should run when the best match is unchanged"
    assert result["skipped"] == 1
    assert result["extracted"] == 0
    assert result["details"][0]["video_id"] == "SAME"


def test_youtube_being_unreachable_does_not_discard_a_stored_match(monkeypatch):
    """find_prediction_video swallows fetch failures and returns None. None means
    'could not look', not 'the stored match was wrong' — clobbering the row on a
    YouTube outage would lose a correct extraction."""
    db = make_db()
    event = make_event(db)
    user = make_pundit(db)
    db.add(NotableExtraction(user_id=user.id, event_id=event.id, video_id="KEEPME"))
    db.commit()

    done = []
    stub(monkeypatch, matches=None, extractions=done)
    result = run_extraction_sweep(db)

    assert done == []
    assert result["skipped"] == 1
    row = db.query(NotableExtraction).filter_by(user_id=user.id, event_id=event.id).one()
    assert row.video_id == "KEEPME"


def test_a_pair_with_no_row_yet_extracts_by_matching_itself(monkeypatch):
    """An untouched pair passes video_id=None so run_extraction does its own
    matching — the re-match above is only for pairs that already have a row."""
    db = make_db()
    event = make_event(db)
    make_pundit(db)

    done = []
    stub(monkeypatch, matches={"video_id": "IGNORED"}, extractions=done)
    result = run_extraction_sweep(db)

    assert done == [None]
    assert result["extracted"] == 1


def test_reextract_forces_a_redo_without_consulting_the_matcher(monkeypatch):
    """The blunt override still works and still skips the re-match entirely."""
    db = make_db()
    event = make_event(db)
    user = make_pundit(db)
    db.add(NotableExtraction(user_id=user.id, event_id=event.id, video_id="SAME"))
    db.commit()

    def explode(channel_id, event):
        raise AssertionError("reextract must not bother re-matching")

    done = []
    monkeypatch.setattr(predictions_ai, "find_prediction_video", explode)

    def fake_run_extraction(db, user, event, video_id=None):
        done.append(video_id)
        return {"ok": True, "video_id": "SAME", "created": 1, "updated": 0}

    monkeypatch.setattr(predictions_ai, "run_extraction", fake_run_extraction)
    result = run_extraction_sweep(db, reextract=True)

    assert done == [None]
    assert result["extracted"] == 1
