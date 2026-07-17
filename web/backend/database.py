"""
Database connection setup. Three objects come out of this file:
  - engine        : manages the actual connection to the DB file
  - SessionLocal  : a factory that hands out short-lived sessions
  - Base          : the parent class every table model inherits from
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Keep the SQLite file in a `data/` folder at the PROJECT ROOT — deliberately
# OUTSIDE web/backend, which uvicorn's --reload watches. If the DB lived inside a
# watched folder, every write would look like a code change and restart the server
# in an endless loop. parents[2] = the project root (.../web/backend/database.py).
DB_DIR = Path(__file__).resolve().parents[2] / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "app.db"

# WHERE the data lives depends on the environment. On Railway we set a
# DATABASE_URL env var pointing at the Postgres service (which survives
# redeploys); on a laptop the var is unset, so we fall back to the local
# SQLite file exactly as before.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway sometimes hands out URLs starting with the legacy postgres://
    # scheme, but SQLAlchemy 2 only recognizes postgresql:// — normalize it.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    # check_same_thread=False is a SQLite-only quirk: SQLite normally refuses to
    # let one connection be used by multiple threads, but a web server is
    # multi-threaded, so we relax that rule. (Postgres has no such rule, which
    # is why this arg only exists on this branch.)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# A SESSION is one "conversation" with the database — a unit of work you can
# commit or roll back (a transaction). SessionLocal is a FACTORY: every request
# will call SessionLocal() to get its own fresh session, then close it.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# BASE is the declarative base class. Every model (like User) subclasses it.
# SQLAlchemy uses Base to keep a registry of all tables so it can create them.
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
