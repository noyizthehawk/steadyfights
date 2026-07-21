"""
Database models. Each class here maps to one table.
"""
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint, ForeignKey, JSON, Enum
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


class Pick(Base):
    """One user's prediction for one fight. """
    __tablename__ = "picks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fight_id = Column(Integer, ForeignKey("ufc_fights.id"), nullable=False)
    picked = Column(String, nullable=False)   # the fighter name they chose
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    fight = relationship("UFCFight")

    __table_args__ = (UniqueConstraint("user_id", "fight_id", name="uq_user_fight"),) # a user can't pick twice


class Friendship(Base):
    """A friend relationship between two users. One row covers the whole
    lifecycle: 'pending' when invited, 'accepted' once accepted. Declining just
    deletes the row. Stored once but treated as bidirectional once accepted."""
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # who sent the invite
    addressee_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # who received it
    status = Column(String, default="pending")   # "pending" | "accepted"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # can't invite the same person twice
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_friendship"),)


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

    # Stripe billing — both start empty; filled once the user subscribes.
    # stripe_customer_id links this user to Stripe's Customer (looked up in webhooks).
    stripe_customer_id = Column(String, nullable=True, index=True)
    # Mirror of Stripe's subscription state: "active" / "canceled" / None.
    subscription_status = Column(String, nullable=True)
    free_predictions_used = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<User id={self.id} email={self.email!r}>"
class CoinReason(enum.Enum):
    purchase    = "purchase"      # + bought coins via Stripe
    room_buyin  = "room_buyin"    # − paid to join a room
    room_payout = "room_payout"   # + won a share of the pot
    refund      = "refund"
    

class CoinLedger(Base):
    __tablename__ = "coin_ledger"

    #make sure the db know who a coin belongs to 
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    #reason for moving coins, every row in coin ledger is one coin movement
    reason = Column(Enum(CoinReason), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reference_id = Column(Integer, nullable=True)
    external_id = Column(String, unique=True, nullable=True, index=True)
class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    entry_fee = Column(Integer, nullable=False, default=0)
    closes_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # public = anyone can find it in the lobby; private = only the owner's friends see it
    is_public = Column(Boolean, nullable=False, default=False)
    settled_at = Column(DateTime, nullable=True)

class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="pending", nullable=False)
