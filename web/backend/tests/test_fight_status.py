"""Tests for UFCFight.status — the scheduled/cancelled/completed distinction.

Before this column, winner IS NULL meant three different things at once: not
fought yet, called off, or the scraper failed. That ambiguity caused two real
bugs, and both are pinned here.

Run:  .venv/bin/python -m web.backend.tests.test_fight_status
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import UFCEvent, UFCFight
from ..scraping import save_events


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def scraped(*matchups):
    """Minimal shape of what the scraper hands save_events()."""
    return [{
        "event_link": "/event/ufc-999",
        "title": "UFC 999",
        "date": 4102444800,          # far future so it counts as upcoming
        "venue": "Somewhere",
        "poster": None,
        "fights": [{
            "matchup": m,
            "fighter_a": m.split(" vs ")[0],
            "fighter_b": m.split(" vs ")[1],
            "odds_a": None, "odds_b": None, "img_a": None, "img_b": None,
        } for m in matchups],
    }]


def fights_by_matchup(db):
    return {f.matchup: f for f in db.query(UFCFight).all()}


def test_new_fights_start_scheduled():
    db = make_db()
    save_events(scraped("Jon Jones vs Tom Aspinall"), db)
    assert fights_by_matchup(db)["Jon Jones vs Tom Aspinall"].status == "scheduled"


def test_a_bout_that_leaves_the_card_is_cancelled_not_deleted():
    """The bug this column exists for: upsert-by-matchup never deletes, so when
    a fighter pulls out the old row survives next to the replacement and the
    fighter appears twice on one card."""
    db = make_db()
    save_events(scraped("Jon Jones vs Tom Aspinall"), db)
    # Aspinall withdraws; Jones now faces Gane. The card no longer lists the old bout.
    save_events(scraped("Jon Jones vs Ciryl Gane"), db)

    rows = fights_by_matchup(db)
    assert len(rows) == 2, "the old row must survive — settled picks still reference it"
    assert rows["Jon Jones vs Tom Aspinall"].status == "cancelled"
    assert rows["Jon Jones vs Ciryl Gane"].status == "scheduled"


def test_a_rebooked_bout_goes_back_to_scheduled():
    """Withdrawals get reversed — an injury clears, the bout returns to the card."""
    db = make_db()
    save_events(scraped("Jon Jones vs Tom Aspinall"), db)
    save_events(scraped("Jon Jones vs Ciryl Gane"), db)
    assert fights_by_matchup(db)["Jon Jones vs Tom Aspinall"].status == "cancelled"

    save_events(scraped("Jon Jones vs Tom Aspinall", "Jon Jones vs Ciryl Gane"), db)
    assert fights_by_matchup(db)["Jon Jones vs Tom Aspinall"].status == "scheduled"


def test_completed_bouts_are_not_cancelled_when_they_leave_the_card():
    """A finished event legitimately stops listing its bouts. Those already
    happened and must keep their result — only 'scheduled' rows can be cancelled."""
    db = make_db()
    save_events(scraped("Jon Jones vs Tom Aspinall"), db)
    fight = fights_by_matchup(db)["Jon Jones vs Tom Aspinall"]
    fight.winner = "Jon Jones"
    fight.status = "completed"
    db.commit()

    save_events(scraped("Someone Else vs Another Guy"), db)

    fight = fights_by_matchup(db)["Jon Jones vs Tom Aspinall"]
    assert fight.status == "completed"
    assert fight.winner == "Jon Jones"


def test_settle_stops_rescraping_an_event_whose_only_open_bout_was_cancelled():
    """run_settle selected events with any winner IS NULL. A cancelled bout keeps
    a NULL winner forever, so the event matched on every single run."""
    from ..models import UFCEvent as E
    db = make_db()
    save_events(scraped("A Fighter vs B Fighter", "C Fighter vs D Fighter"), db)
    rows = fights_by_matchup(db)
    rows["A Fighter vs B Fighter"].winner = "A Fighter"
    rows["A Fighter vs B Fighter"].status = "completed"
    rows["C Fighter vs D Fighter"].status = "cancelled"      # pulled, never fought
    db.commit()

    # the old predicate: still matches, forever
    stale = db.query(E).filter(E.fights.any(UFCFight.winner.is_(None))).count()
    # the new one: nothing left to settle
    fresh = db.query(E).filter(E.fights.any(UFCFight.status == "scheduled")).count()
    assert stale == 1, "old filter would keep re-scraping this event"
    assert fresh == 0, "new filter correctly leaves it alone"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
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
