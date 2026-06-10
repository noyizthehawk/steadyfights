"""
Database connection setup. Three objects come out of this file:
  - engine        : manages the actual connection to the DB file
  - SessionLocal  : a factory that hands out short-lived sessions
  - Base          : the parent class every table model inherits from
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Put the SQLite file right next to this code, as an ABSOLUTE path, so it lands
# in the same place no matter which folder you run the server from.
DB_PATH = Path(__file__).resolve().parent / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# The ENGINE is the low-level gateway to the database. It knows the URL and
# manages a pool of connections. Nothing talks to the DB without going through it.
# check_same_thread=False is a SQLite-only quirk: SQLite normally refuses to let
# one connection be used by multiple threads, but a web server is multi-threaded,
# so we relax that rule.
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
