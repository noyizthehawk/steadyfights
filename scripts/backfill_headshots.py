"""Backfill fighter pictures for anyone the event scrape never pictured.

For each fighter without an event-card headshot, tries their ufc.com athlete
page, then their Wikipedia article's photo on Wikimedia Commons (stored with
the credit its licence requires). Results land in fighter_headshots; a fighter
with nothing found is recorded too, so re-runs don't re-request dead pages.

Reads DATABASE_URL the same way the app does, so to fill production:
    DATABASE_URL="<railway public url>" python3 scripts/backfill_headshots.py

    python3 scripts/backfill_headshots.py               # top 50 careers + leaderboards + next card
    python3 scripts/backfill_headshots.py --top 200     # go deeper
    python3 scripts/backfill_headshots.py --retry-missing   # re-check "nothing found"
"""
import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web.backend.database import SessionLocal  # noqa: E402
from web.backend.models import UFCEvent  # noqa: E402
from web.backend.event_timing import EVENT_DURATION  # noqa: E402
from web.backend import headshots  # noqa: E402
from part_2 import career  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--top", type=int, default=50, help="how many top careers to cover (default 50)")
    p.add_argument("--retry-missing", action="store_true",
                   help="re-check fighters previously recorded as having no picture")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    db = SessionLocal()
    try:
        names = [r["fighter"] for r in career.top_careers(n=args.top)]
        # everyone on the page's fun lists (in form, tallest, ...)
        names += [row["fighter"] for rows in career.leaderboards().values() for row in rows]
        # The next card's fighters usually have event headshots already; this
        # catches late replacements the scrape hasn't pictured yet.
        event = (db.query(UFCEvent)
                 .filter(UFCEvent.date > int(time.time()) - EVENT_DURATION)
                 .order_by(UFCEvent.date).first())
        if event:
            names += [n for f in event.fights for n in (f.fighter_a, f.fighter_b) if n]

        stats = headshots.backfill(db, list(dict.fromkeys(names)),
                                   delay=args.delay, retry_missing=args.retry_missing)
        print(f"\nufc.com: {stats['ufc']}  commons: {stats['commons']}  "
              f"none found: {stats['none']}  already had one: {stats['skipped']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
