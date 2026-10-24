"""Which events the site lists as upcoming: only ones with a live main event.

Run:  .venv/bin/python -m pytest web/backend/tests/test_upcoming_events.py
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import UFCEvent, UFCFight
from ..routers import events, predict

NOW = 1_800_000_000


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def add_event(db, title, bouts, days_out=7):
    """bouts: (fighter_a, fighter_b, status) tuples."""
    event = UFCEvent(title=title, event_link=f"/event/{title}", date=NOW + days_out * 86400)
    db.add(event)
    db.flush()
    for a, b, status in bouts:
        db.add(UFCFight(event_id=event.id, matchup=f"{a} vs {b}", fighter_a=a, fighter_b=b, status=status))
    db.commit()
    return event


def titles(db):
    return [e.title for e in events.upcoming_events(db, NOW)]


def test_event_with_its_main_event_is_listed():
    db = make_db()
    add_event(db, "Jones vs Aspinall", [("Jon Jones", "Tom Aspinall", "scheduled"),
                                        ("A B", "C D", "scheduled")])
    assert titles(db) == ["Jones vs Aspinall"]


def test_placeholder_without_a_headliner_is_hidden():
    # far-off "UFC Fight Night" with only prelims announced
    db = make_db()
    add_event(db, "UFC Fight Night", [("A B", "C D", "scheduled")], days_out=60)
    add_event(db, "Jones vs Aspinall", [("Jon Jones", "Tom Aspinall", "scheduled")])
    assert titles(db) == ["Jones vs Aspinall"]


def test_cancelled_headliner_hides_the_event():
    db = make_db()
    add_event(db, "Jones vs Aspinall", [("Jon Jones", "Tom Aspinall", "cancelled"),
                                        ("A B", "C D", "scheduled")])
    assert titles(db) == []


def test_fighters_page_next_card_skips_hidden_events():
    db = make_db()
    add_event(db, "UFC Fight Night", [("A B", "C D", "scheduled")], days_out=3)   # sooner, but hidden
    add_event(db, "Jones vs Aspinall", [("Jon Jones", "Tom Aspinall", "scheduled")], days_out=7)
    import time
    from unittest.mock import patch
    with patch.object(time, "time", return_value=NOW), \
         patch.object(predict.career, "top_careers", return_value=[]), \
         patch.object(predict.career, "leaderboards", return_value={}), \
         patch.object(predict, "LEADERBOARDS", []), \
         patch.object(predict.career, "fighter_tag", return_value=None):
        out = predict.browse_fighters(db)
    assert out["next_card"]["event"]["title"] == "Jones vs Aspinall"


def test_next_card_lists_each_fighter_once_from_their_newest_bout():
    # Aspinall pulls out: the old bout stays as cancelled, Jones is rebooked
    # with Gane; and a stale double booking leaves Smith in two live bouts
    db = make_db()
    event = add_event(db, "Jones vs Gane", [
        ("Jon Jones", "Tom Aspinall", "cancelled"),
        ("Jon Jones", "Ciryl Gane", "scheduled"),
        ("Joe Smith", "Old Opponent", "scheduled"),
        ("Joe Smith", "New Opponent", "scheduled"),
    ])
    names = predict._card_fighters(event)
    assert names.count("Jon Jones") == 1 and names.count("Joe Smith") == 1
    assert "Tom Aspinall" not in names                 # only in the cancelled bout
    assert "Old Opponent" in names                     # still booked, just not with Smith now
    assert names.index("Joe Smith") == names.index("New Opponent") - 1   # Smith from the newer bout
