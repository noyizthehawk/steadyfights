"""Dev helper: hand a local user their free predictions back.

/api/predict burns one of FREE_PREDICTION_LIMIT (10) free predictions per call
for any user without an active subscription, which runs out fast while working
on the UI. This resets the counter straight in the DB.

Local use only. It reads DATABASE_URL the same way the app does, so it will
happily point at production if that var is set -- it refuses to run in that
case unless you pass --i-know-this-is-not-local.

    python3 scripts/reset_free_predictions.py                 # list users
    python3 scripts/reset_free_predictions.py --all           # reset everyone
    python3 scripts/reset_free_predictions.py --user noya     # by email or username
    python3 scripts/reset_free_predictions.py --user noya --subscribe
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web.backend.database import SessionLocal, DATABASE_URL  # noqa: E402
from web.backend.models import User  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", help="email or username (case-insensitive); omit with --all")
    p.add_argument("--all", action="store_true", help="reset every user in the DB")
    p.add_argument("--subscribe", action="store_true",
                   help="also set subscription_status='active' (unlimited, and exercises the subscriber path)")
    p.add_argument("--unsubscribe", action="store_true",
                   help="clear subscription_status, back to the free-tier path")
    p.add_argument("--i-know-this-is-not-local", action="store_true")
    args = p.parse_args()

    if os.getenv("DATABASE_URL") and not args.i_know_this_is_not_local:
        sys.exit(f"refusing to run: DATABASE_URL is set ({DATABASE_URL.split('@')[-1]}). "
                 f"This script is for the local SQLite DB.")

    db = SessionLocal()
    try:
        if args.all:
            targets = db.query(User).all()
        elif args.user:
            needle = args.user.lower()
            targets = [u for u in db.query(User).all()
                       if u.email.lower() == needle or u.username.lower() == needle]
            if not targets:
                sys.exit(f"no user matching {args.user!r}")
        else:
            # No target: just report, change nothing.
            rows = db.query(User).order_by(User.id).all()
            if not rows:
                sys.exit("no users in the local DB yet -- sign up in the app first.")
            print(f"{'id':>3}  {'username':<20} {'email':<28} {'used':>4}  subscription")
            for u in rows:
                print(f"{u.id:>3}  {u.username:<20} {u.email:<28} "
                      f"{u.free_predictions_used:>4}  {u.subscription_status or '-'}")
            print("\npass --user <email|username> or --all to reset")
            return

        for u in targets:
            before = u.free_predictions_used
            u.free_predictions_used = 0
            if args.subscribe:
                u.subscription_status = "active"
            elif args.unsubscribe:
                u.subscription_status = None
            print(f"{u.username} ({u.email}): used {before} -> 0, "
                  f"subscription={u.subscription_status or '-'}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
