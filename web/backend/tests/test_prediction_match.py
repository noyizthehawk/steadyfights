"""Tests for find_prediction_video — picking a pundit's prediction video for an event.

The matcher scores every recent upload on a channel and takes the best. Getting
it wrong is expensive and silent: the winning video's id is written into
NotableExtraction as that pundit's source for the card, and its transcript is
what Gemini reads picks out of. A wrong match means wrong picks attributed to a
real person, with nothing in the logs to say so.

Three bugs found by scoring real titles against the real UFC 331 row are pinned
here, all of them in tokenisation rather than in the weights:

  * "Ruffy!" did not equal "ruffy", because normalize_name leaves punctuation
    alone and matching is on whitespace-split tokens. Two surnames are needed to
    clear the `specific >= 2` gate, so one trailing "!" could reject a correct
    video outright.
  * "Van vs Pantoja 2" produced the headliner set {"van"} — splitting on "vs"
    leaves the tail token "2", which the length filter then discarded, demoting
    Pantoja to a non-headliner worth half as much.
  * "Rosas Jr." contributed the surname "jr", which matched any title mentioning
    a junior and handed it a free point toward that same gate.

Run:  .venv/bin/python -m pytest web/backend/tests/test_prediction_match.py
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..database import Base
from ..models import UFCEvent, UFCFight
from .. import predictions_ai
from ..predictions_ai import find_prediction_video, _last_names

DAY = 86400
EVENT_DATE = 1789273559          # the real UFC 331 timestamp


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def make_event(db, title="Van vs Pantoja 2", link="/event/cryptocom-ufc-331",
               venue="Crypto.com Arena", series=None, matchups=(
                   "Joshua Van vs Alexandre Pantoja",
                   "Arman Tsarukyan vs Mauricio Ruffy",
                   "Brian Ortega vs Diego Lopes",
               )):
    event = UFCEvent(title=title, event_link=link, date=EVENT_DATE,
                     venue=venue, series=series)
    db.add(event)
    db.flush()
    for i, m in enumerate(matchups):
        a, b = m.split(" vs ")
        db.add(UFCFight(event_id=event.id, matchup=m, fighter_a=a, fighter_b=b,
                        bout_order=i + 1, card_section="Main Card"))
    db.commit()
    db.refresh(event)
    return event


def upload(video_id, title, days_before):
    """One item in the shape fetch_channel_uploads returns."""
    published = EVENT_DATE - days_before * DAY
    stamp = __import__("datetime").datetime.fromtimestamp(
        published, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"video_id": video_id, "title": title, "published_at": stamp}


def pick(monkeypatch, event, uploads):
    """Run the matcher over exactly `uploads`, returning the chosen video id."""
    monkeypatch.setattr(predictions_ai, "fetch_channel_uploads",
                        lambda channel_id, limit=30: uploads)
    match = find_prediction_video("UC00000000000000000000", event)
    return match["video_id"] if match else None


# ── the case that prompted the audit ───────────────────────────────────────────

def test_recent_full_card_beats_an_older_rant_about_the_headline_fight(monkeypatch):
    """A rant names two fighters and the event number, so it clears the gate. It
    loses on the content bonuses — 'reaction' and 'rant' earn nothing, which is
    exactly what full card/breakdown/predictions are weighted to separate."""
    db = make_db()
    event = make_event(db)
    chosen = pick(monkeypatch, event, [
        upload("RANT", "The Fight NO ONE Asked For! Tsarukyan vs Ruffy Is A JOKE! "
                       "UFC 331 Reaction & Rant", days_before=30),
        upload("FULLCARD", "My Full Card Predictions & Breakdown For UFC 331",
               days_before=3),
    ])
    assert chosen == "FULLCARD"


# ── bug 1: punctuation ────────────────────────────────────────────────────────

def test_surname_followed_by_punctuation_still_matches(monkeypatch):
    """'Ruffy!' must score as 'ruffy'. With no event number in the title these
    two surnames are the only evidence, so losing one to '!' drops the video."""
    db = make_db()
    event = make_event(db)
    assert pick(monkeypatch, event, [
        upload("PUNCT", "PREDICTIONS: Tsarukyan vs. Ruffy!", days_before=2),
    ]) == "PUNCT"


def test_hyphenated_event_number_matches(monkeypatch):
    """'UFC-331' is how plenty of titles are written; the number regex only
    tolerates whitespace, so the hyphen has to be flattened before it."""
    db = make_db()
    event = make_event(db)
    assert pick(monkeypatch, event, [
        upload("HYPHEN", "Full Card Predictions - UFC-331", days_before=4),
    ]) == "HYPHEN"


# ── bug 2: rematch digits ─────────────────────────────────────────────────────

def test_rematch_digit_does_not_drop_the_headliner():
    """'Van vs Pantoja 2' must yield both headliners, not just Van."""
    assert _last_names(["Joshua Van ", " Alexandre Pantoja 2"]) == {"van", "pantoja"}


def test_a_rematch_headliner_named_alone_clears_the_gate(monkeypatch):
    """A headliner is worth 2, which is exactly the gate — so naming one is
    enough on its own. While the rematch digit demoted Pantoja to a 1-point
    undercard name this scored 1, and a correct video was thrown away."""
    db = make_db()
    event = make_event(db)
    assert pick(monkeypatch, event, [
        upload("PANTOJA", "Pantoja Full Card Predictions & Breakdown", days_before=4),
    ]) == "PANTOJA"


# ── bug 3: generational suffixes ──────────────────────────────────────────────

def test_generational_suffix_is_not_a_surname():
    """'Rosas Jr.' is Rosas. 'jr' as a surname matched any title mentioning one."""
    assert _last_names(["Raul Rosas Jr."]) == {"rosas"}
    assert _last_names(["Andre Muniz Sr", "Khalil Rountree Jr"]) == {"muniz", "rountree"}


def test_a_junior_in_an_unrelated_title_is_not_a_surname_match(monkeypatch):
    """A different card's video, sharing only the common surname Rodriguez. That
    is one point and correctly below the gate — but while 'jr' was itself a
    surname, the unrelated junior in the title added the second point and this
    video was matched to the wrong event."""
    db = make_db()
    event = make_event(db, matchups=("Raul Rosas Jr. vs Raoni Barcelos",
                                     "Joshua Van vs Alexandre Pantoja",
                                     "Bogdan Guskov vs Daniel Rodriguez"))
    assert pick(monkeypatch, event, [
        upload("OTHER", "Rodriguez vs Silva Jr. — Full Card Predictions", days_before=6),
    ]) is None


# ── the gate that stops cross-event matches ───────────────────────────────────

def test_a_video_about_a_different_card_is_rejected(monkeypatch):
    """The regression the `specific >= 2` gate exists for: one shared common
    surname plus strong generic bonuses used to win. 'Rodriguez' appears on many
    cards; alone it is not evidence about this one."""
    db = make_db()
    event = make_event(db, matchups=("Joshua Van vs Alexandre Pantoja",
                                     "Bogdan Guskov vs Daniel Rodriguez"))
    assert pick(monkeypatch, event, [
        upload("BELGRADE", "Medic vs Rodriguez — UFC Belgrade Full Card "
                           "Predictions & Breakdown", days_before=8),
    ]) is None


def test_nothing_matches_returns_none(monkeypatch):
    db = make_db()
    event = make_event(db)
    assert pick(monkeypatch, event, [
        upload("VLOG", "I Bought Every Protein Powder So You Don't Have To",
               days_before=1),
    ]) is None


# ── the plausibility window ───────────────────────────────────────────────────

def test_a_video_published_long_before_the_card_is_skipped(monkeypatch):
    """Outside the window the video is dropped regardless of how well it scores."""
    db = make_db()
    event = make_event(db)
    assert pick(monkeypatch, event, [
        upload("ANCIENT", "Full Card Predictions & Breakdown For UFC 331",
               days_before=200),
    ]) is None


def test_a_video_published_well_after_the_card_is_skipped(monkeypatch):
    db = make_db()
    event = make_event(db)
    assert pick(monkeypatch, event, [
        upload("RECAP", "Full Card Predictions & Breakdown For UFC 331",
               days_before=-40),
    ]) is None


def test_no_uploads_returns_none(monkeypatch):
    db = make_db()
    event = make_event(db)
    assert pick(monkeypatch, event, []) is None


def test_a_fetch_failure_is_swallowed(monkeypatch):
    """A YouTube outage must not take down extraction for every user."""
    db = make_db()
    event = make_event(db)

    def boom(channel_id, limit=30):
        raise RuntimeError("youtube is down")

    monkeypatch.setattr(predictions_ai, "fetch_channel_uploads", boom)
    assert find_prediction_video("UC00000000000000000000", event) is None
