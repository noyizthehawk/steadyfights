"""
Run from the PROJECT ROOT:
    python -m web.backend.settle
"""
from .database import SessionLocal
from .scraping import run_settle
from .routers.groups import run_settle_rooms


def main():
    db = SessionLocal()
    try:
        # 1) settle fights FIRST — room leaderboards rank on settled picks
        fights = run_settle(db)
        print(f"Settled {fights['settled']} fight(s) "
              f"across {fights['events']} finished event(s).")
        # 2) THEN pay out any rooms whose close time has passed
        rooms = run_settle_rooms(db)
        print(f"Paid out {rooms['settled']} room(s) "
              f"({rooms['failed']} failed) of {rooms['rooms']} due.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
