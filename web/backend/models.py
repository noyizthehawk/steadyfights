"""
Database models. Each class here maps to one table.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint, ForeignKey, JSON

from sqlalchemy.orm import relationship
from .database import Base


class UFCEvent(Base):
    __tablename__ = "ufc_events"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    event_link = Column(String, unique=True)  # preventing dups
    date = Column(Integer)  
    venue = Column(String)
    poster = Column(String)
    odds = Column(JSON)      # store odds as JSON
    fights = relationship("UFCFight", back_populates="event", cascade="all, delete-orphan")

class UFCFight(Base):
    __tablename__ = "ufc_fights"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("ufc_events.id"))
    matchup = Column(String)
    red_corner_img = Column(String)
    blue_corner_img = Column(String)
    event = relationship("UFCEvent", back_populates="fights")

    __table_args__ = (UniqueConstraint("event_id", "matchup"),)

class User(Base):
    # The actual table name in the database.
    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # The login identifier. unique=True means the DB itself forbids two users same adress
    email = Column(String, unique=True, index=True, nullable=False)

    # We store the bcrypt HASH of the password, never the password itself
    hashed_password = Column(String, nullable=False)

    # When the account was created. 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User id={self.id} email={self.email!r}>"


class Fight(Base):
    """One UFC bout users can predict. Populated from the lemur/ufc-api actor.
    `winner` stays NULL until the fight happens; then we settle picks against it."""
    __tablename__ = "fights"

    id = Column(Integer, primary_key=True, index=True)

    event_slug = Column(String, index=True, nullable=False)   # e.g. "ufc-323"
    event = Column(String)                                    # display name
    matchup = Column(String)                                  # "Makhachev vs ..."

    fighter_a = Column(String, nullable=False)
    fighter_b = Column(String, nullable=False)

    # American odds (e.g. -250 / +180). May be missing for some bouts.
    odds_a = Column(Integer, nullable=True)
    odds_b = Column(Integer, nullable=True)

    is_title_fight = Column(Boolean, default=False)
    locks_at = Column(DateTime, nullable=True)   # picks close at the fight's start

    # NULL = not settled yet. Filled with the winner's name after the bout.
    winner = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # The same bout must never be inserted twice — lets us UPSERT on refresh
    # (re-fetching the card to update odds, or to fill in the winner).
    __table_args__ = (
        UniqueConstraint("event_slug", "fighter_a", "fighter_b", name="uq_fight"),
    )

    def __repr__(self):
        return f"<Fight {self.fighter_a} vs {self.fighter_b} ({self.event_slug})>"
        
