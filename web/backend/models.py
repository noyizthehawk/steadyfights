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
    fights = relationship("UFCFight", back_populates="event", cascade="all, delete-orphan")

class UFCFight(Base):
    __tablename__ = "ufc_fights"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("ufc_events.id"))
    matchup = Column(String)
    fighter_a = Column(String)
    fighter_b = Column(String)
    odds_a = Column(String, nullable=True)
    odds_b = Column(String, nullable=True)
    img_a = Column(String, nullable=True)    # fighter headshot URLs from ufc.com
    img_b = Column(String, nullable=True)
    winner = Column(String, nullable=True)
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

