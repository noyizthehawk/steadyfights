"""
Run from the PROJECT ROOT:
    python -m web.backend.settle
"""
from .database import SessionLocal
from .scraping import run_settle


def main():
    db = SessionLocal()
    try:
        result = run_settle(db)
        print(f"Settled {result['settled']} fight(s) "
              f"across {result['events']} finished event(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
