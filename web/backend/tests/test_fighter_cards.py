"""Tests for the Fighters page: picture priority, the best-metric rule, slugs.

No network: fetch_ufc / fetch_commons are stubbed, and the DB is in-memory.
Run:  .venv/bin/python -m pytest web/backend/tests/test_fighter_cards.py
"""
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import FighterHeadshot, UFCEvent, UFCFight
from .. import headshots
from ..routers import predict


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _event_with_headshot(db, name, img, date=1_700_000_000):
    event = UFCEvent(title="UFC Test", event_link=f"https://x/{img}", date=date)
    db.add(event)
    db.flush()
    db.add(UFCFight(event_id=event.id, fighter_a=name, fighter_b="Someone Else", img_a=img))
    db.commit()


def test_ufc_slug():
    assert headshots.ufc_slug("Georges St-Pierre") == "georges-st-pierre"
    assert headshots.ufc_slug("José Aldo") == "jose-aldo"
    assert headshots.ufc_slug("Sean O'Malley") == "sean-omalley"
    assert headshots.ufc_slug("B.J. Penn") == "bj-penn"


def test_event_headshot_beats_backfill():
    db = make_db()
    _event_with_headshot(db, "Jon Jones", "event.png")
    db.add(FighterHeadshot(fighter_norm="jon jones", fighter="Jon Jones",
                           image_url="backfill.png", source="ufc"))
    db.commit()
    pic = headshots.lookup(db, ["Jon Jones"])["jon jones"]
    assert pic["image_url"] == "event.png" and pic["credit"] is None


def test_newest_event_headshot_wins():
    db = make_db()
    _event_with_headshot(db, "Jon Jones", "old.png", date=1_600_000_000)
    _event_with_headshot(db, "Jon Jones", "new.png", date=1_700_000_000)
    assert headshots.lookup(db, ["Jon Jones"])["jon jones"]["image_url"] == "new.png"


def test_commons_picture_carries_credit_and_missing_is_none():
    db = make_db()
    db.add(FighterHeadshot(fighter_norm="randy couture", fighter="Randy Couture",
                           image_url="c.jpg", source="commons", credit_author="Gage Skidmore",
                           credit_license="CC BY-SA 3.0", credit_url="https://commons/x"))
    db.add(FighterHeadshot(fighter_norm="nobody", fighter="Nobody", image_url=None))
    db.commit()
    out = headshots.lookup(db, ["Randy Couture", "Nobody"])
    assert out["randy couture"]["credit"] == {
        "author": "Gage Skidmore", "license": "CC BY-SA 3.0", "url": "https://commons/x"}
    assert out["nobody"]["image_url"] is None


def test_backfill_tries_ufc_then_commons_and_records_misses():
    db = make_db()
    commons = {"image_url": "c.jpg", "credit_author": None,
               "credit_license": "Public domain", "credit_url": "u"}
    with patch.object(headshots, "fetch_ufc", side_effect=lambda n: "u.png" if n == "A Fighter" else None), \
         patch.object(headshots, "fetch_commons", side_effect=lambda n: commons if n == "B Fighter" else None):
        stats = headshots.backfill(db, ["A Fighter", "B Fighter", "C Fighter"], delay=0)
    assert stats == {"ufc": 1, "commons": 1, "none": 1, "skipped": 0}
    rows = {r.fighter: r for r in db.query(FighterHeadshot)}
    assert rows["A Fighter"].source == "ufc"
    assert rows["B Fighter"].source == "commons" and rows["B Fighter"].credit_license == "Public domain"
    assert rows["C Fighter"].image_url is None          # recorded, so re-runs skip it

    # a second run re-requests nothing
    with patch.object(headshots, "fetch_ufc") as fu, patch.object(headshots, "fetch_commons") as fc:
        stats = headshots.backfill(db, ["A Fighter", "B Fighter", "C Fighter"], delay=0)
    assert stats["skipped"] == 3 and not fu.called and not fc.called


# A tiny fixed roster so these tests don't depend on the real data: each stat
# has 10 fighters, evenly spread, with sapm where LOWER is better.
_ROSTER = {
    "str_acc": [30, 35, 40, 42, 45, 47, 50, 53, 56, 60],
    "str_def": [40, 45, 50, 52, 55, 57, 59, 61, 63, 66],
    "td_acc":  [0, 15, 25, 30, 38, 42, 48, 55, 62, 70],
    "td_def":  [30, 45, 55, 60, 65, 70, 75, 80, 88, 95],
    "slpm":    [1.6, 2.2, 2.7, 3.0, 3.4, 3.8, 4.2, 4.8, 5.4, 6.2],
    "sapm":    [1.6, 2.2, 2.7, 3.0, 3.3, 3.7, 4.1, 4.7, 5.3, 6.0],
    "td_avg":  [0, 0.3, 0.6, 1.0, 1.3, 1.7, 2.1, 2.7, 3.4, 4.5],
    "sub_avg": [0, 0, 0.1, 0.2, 0.4, 0.5, 0.7, 0.9, 1.3, 2.0],
}


def _best(stats, fights):
    import numpy as np
    dist = {k: np.sort(np.array(v, dtype=float)) for k, v in _ROSTER.items()}
    with patch.object(predict.career, "_stat_distribution", return_value=dist), \
         patch.object(predict.career, "get_fighter_stats", return_value=stats):
        return predict._best_metric("X", total_fights=fights)


def test_best_metric_compares_each_stat_against_its_own_spread():
    # 70% TD defence is the biggest raw number but only mid-pack for that stat
    # (beats 5 of 10); 58% striking accuracy beats 9 of 10, so it wins
    best = _best({"str_acc": 58.0, "td_def": 70.0}, fights=12)
    assert best["key"] == "str_acc" and best["display"] == "58%"
    assert best["top_pct"] == 10


def test_lower_absorbed_is_better():
    assert _best({"sapm": 1.5, "slpm": 3.0}, fights=12)["key"] == "sapm"
    assert _best({"sapm": 5.8, "slpm": 3.0}, fights=12)["key"] == "slpm"
    shown = _best({"sapm": 1.5}, fights=12)
    assert shown["display"] == "1.5" and shown["percentile"] == 100.0 and shown["top_pct"] == 1


def test_best_metric_skips_grappling_for_few_fights():
    stats = {"str_def": 55.0, "td_def": 100.0, "sub_avg": 3.0}
    assert _best(stats, fights=3)["key"] == "str_def"     # 100% TD def over 3 fights ignored
    assert _best(stats, fights=12)["key"] in {"td_def", "sub_avg"}


def test_ties_count_half():
    # 0 subs ties with the two zeros at the bottom: worse than none, tied with 2
    # -> (0 + 2/2) / 10 = 10th percentile, not 0th and not 20th
    from part_2 import career
    import numpy as np
    dist = {k: np.sort(np.array(v, dtype=float)) for k, v in _ROSTER.items()}
    with patch.object(career, "_stat_distribution", return_value=dist):
        assert career.stat_percentile("sub_avg", 0.0) == 10.0


def test_best_metric_none_without_stats():
    with patch.object(predict.career, "get_fighter_stats", return_value=None):
        assert predict._best_metric("X", total_fights=10) is None


def test_flag_comes_from_newest_event_that_has_one():
    db = make_db()
    old = UFCEvent(title="Old", event_link="https://x/old", date=1_600_000_000)
    new = UFCEvent(title="New", event_link="https://x/new", date=1_700_000_000)
    db.add_all([old, new])
    db.flush()
    db.add(UFCFight(event_id=old.id, fighter_a="Jon Jones", fighter_b="Z",
                    flag_a="https://ufc.com/images/flags/US.PNG", country_a="United States"))
    # newest card has a headshot but no flag — must not blank out the older flag
    db.add(UFCFight(event_id=new.id, fighter_a="Jon Jones", fighter_b="Z", img_a="new.png"))
    db.commit()
    out = headshots.lookup(db, ["Jon Jones", "Never Scraped"])
    assert out["jon jones"]["image_url"] == "new.png"
    assert out["jon jones"]["country"] == "United States"
    assert out["never scraped"]["flag_url"] is None


def test_browse_leaderboards_carry_their_own_stat():
    db = make_db()
    boards = {b["key"]: [] for b in predict.LEADERBOARDS}
    boards["tallest"] = [{"fighter": "Tall Guy", "value": 200.7, "display": "6'7\" · 201 cm",
                          "fill": 100.0, "note": "Reach 203 cm"}]
    with patch.object(predict.career, "leaderboards", return_value=boards), \
         patch.object(predict.career, "top_careers", return_value=[]), \
         patch.object(predict.career, "fighter_tag", return_value=None):
        out = predict.browse_fighters(db)
    assert [b["key"] for b in out["leaderboards"]] == [b["key"] for b in predict.LEADERBOARDS]
    tallest = next(b for b in out["leaderboards"] if b["key"] == "tallest")
    card = tallest["fighters"][0]
    assert card["name"] == "Tall Guy"
    assert card["highlight"] == {"label": "Height", "value": 200.7, "display": "6'7\" · 201 cm",
                                 "fill": 100.0, "note": "Reach 203 cm"}
