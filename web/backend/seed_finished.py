"""Seed ONE real, finished UFC event so the settle pipeline can be tested.

Unlike seed_data.py (which fakes winners at random), this inserts a real card's
fights with winner=None and a PAST date. You then hit POST /api/settle-events to
fill in the actual winners scraped from ufc.com — exercising the whole chain:
scrape_winners -> settle_event -> the DB.

Run from the PROJECT ROOT:
    python -m web.backend.seed_finished
"""
import time

from .database import SessionLocal
from .scraping import scrape_event_details, save_events
from .models import UFCEvent

EVENT_LINK = "/event/ufc-fight-night-may-30-2026"  # a finished card on ufc.com


def seed():
    db = SessionLocal()
    try:
        poster, fights = scrape_event_details(EVENT_LINK)
        results = [{
            "title": "UFC Fight Night: May 30, 2026 (TEST)",
            "event_link": EVENT_LINK,
            "date": int(time.time()) - 7 * 86400,  # a week ago -> counts as finished
            "venue": "Test Arena",
            "poster": poster,
            "fights": fights,
        }]
        save_events(results, db)  # stores the fights with winner left as None

        event = db.query(UFCEvent).filter_by(event_link=EVENT_LINK).first()
        unsettled = [f for f in event.fights if f.winner is None]
        print(f"Seeded '{event.title}' with {len(event.fights)} fights "
              f"({len(unsettled)} unsettled). Now POST /api/settle-events.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
