"""Throwaway seed data for testing the leaderboard / picks. NOT for production.

Creates 20 test users (user1..user20@test.com, password 'test1234'), gives each
a random set of picks, and sets winners on ~60% of fights so winrate is
computable. Re-runnable: it resets fight winners and removes old test users first.

Run from the PROJECT ROOT:
    python -m web.backend.seed_data
"""
import random

from .database import SessionLocal
from .models import User, UFCFight, Pick
from .security import hash_password

NUM_USERS = 20
PASSWORD = "test1234"


def seed():
    db = SessionLocal()
    try:
        fights = db.query(UFCFight).all()
        if not fights:
            print("No fights in the DB — scrape events first, then re-run.")
            return

        # 1. Reset all winners, then "settle" a random ~60% so winrate has data.
        for f in fights:
            f.winner = None
        settled = random.sample(fights, k=int(len(fights) * 0.6))
        for f in settled:
            f.winner = random.choice([f.fighter_a, f.fighter_b])

        # 2. Remove previous test users + their picks (so this is re-runnable).
        old_users = db.query(User).filter(User.email.like("user%@test.com")).all()
        for u in old_users:
            db.query(Pick).filter(Pick.user_id == u.id).delete()
            db.delete(u)
        db.flush()

        # 3. Create users, each with a random subset of picks.
        for i in range(1, NUM_USERS + 1):
            user = User(email=f"user{i}@test.com", hashed_password=hash_password(PASSWORD))
            db.add(user)
            db.flush()  # assigns user.id

            chosen = random.sample(fights, k=random.randint(5, len(fights)))
            for f in chosen:
                db.add(Pick(
                    user_id=user.id,
                    fight_id=f.id,
                    picked=random.choice([f.fighter_a, f.fighter_b]),
                ))

        db.commit()
        print(f"Seeded {NUM_USERS} users (password '{PASSWORD}'), "
              f"settled {len(settled)}/{len(fights)} fights.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
