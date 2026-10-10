"""
Database models. Each class here maps to one table.
"""
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint, ForeignKey, JSON, Enum, Index, func
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
    series = Column(String)
    
    fights = relationship(
        "UFCFight",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="[UFCFight.bout_order.is_(None), UFCFight.bout_order, UFCFight.id]",
    )

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

    
    status = Column(String, nullable=False, server_default="scheduled", index=True)

    
    #
    # Not fixed at first scrape: bouts get promoted when a headliner withdraws,
    # and save_events upserts, so a re-scrape corrects the order for free.
    bout_order = Column(Integer, nullable=True)
    # "Main Card" | "Prelims" | "Early Prelims"
    card_section = Column(String, nullable=True)

    
    flag_a = Column(String, nullable=True)
    flag_b = Column(String, nullable=True)
    
    country_a = Column(String, nullable=True)
    country_b = Column(String, nullable=True)

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


class NotableExtraction(Base):
    
    __tablename__ = "notable_extractions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("ufc_events.id"), nullable=False, index=True)
    video_id = Column(String, nullable=False)   # the YouTube video id the picks came from
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # one extraction record per pundit per event
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_notable_extraction"),)


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

    #public display name case insensitive
    username = Column(String, nullable=False)

    # Public URL of the user's avatar in R2 object storage; null until they
    # upload one (the UI falls back to an initials avatar).
    avatar_url = Column(String, nullable=True)

    # We store the bcrypt HASH of the password, never the password itself
    hashed_password = Column(String, nullable=False)

    # When the account was created.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    stripe_customer_id = Column(String, nullable=True, index=True)
    subscription_status = Column(String, nullable=True)
    free_predictions_used = Column(Integer, nullable=False, default=0)
    is_notable = Column(Boolean, nullable=False, default=False)
    youtube_channel_id = Column(String, nullable=True)

    __table_args__ = (
        # Case-insensitive uniqueness: two rows can't share a username that
        # differs only in case. A plain unique=True would treat "Mike"/"mike"
        # as distinct; indexing lower(username) collapses them.
        Index("uq_users_username_lower", func.lower(username), unique=True),
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email!r} username={self.username!r}>"
class RefreshToken(Base):
    
    # The actual table name in the database.
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    token_hash = Column(String(64), unique=True, nullable=False, index=True)

    family_id = Column(String(36), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    replaced_by = Column(Integer, ForeignKey("refresh_tokens.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<RefreshToken id={self.id} user={self.user_id} family={self.family_id[:8]}>"


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
    # Owner-uploaded cover photo in R2; null = the UI draws the generated
    # RoomCover from the room id instead. Nulled again if enough users report it.
    cover_url = Column(String, nullable=True)

class RoomCoverReport(Base):
    """One user flagging one room's current cover photo.

    Reports are about the IMAGE, not the room: uploading a new cover deletes
    the room's reports, so votes against an old picture can't take down the
    new one. The unique constraint makes one-report-per-user hold in the
    database, like CommentVote.
    """
    __tablename__ = "room_cover_reports"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_room_cover_reports_one_per_user"),
    )

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # the URL that was reported, so an admin can still see what it was after
    # the cover has been taken down
    cover_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="pending", nullable=False)


class EventComment(Base):
    """One comment on an event page.

    A reply is a row in THIS table with parent_id set — there is no `replies`
    column. The child always points up; storing a list on the parent would mean
    the same reply lived in two places and every edit rewrote the parent row.
    """
    __tablename__ = "event_comments"
    __table_args__ = (
        Index("ix_event_comments_feed", "event_id", "parent_id", "id"),
    )

    id = Column(Integer, primary_key=True)
    
    event_id = Column(Integer, ForeignKey("ufc_events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent_id = Column(Integer, ForeignKey("event_comments.id"), nullable=True, index=True)

    body = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User")
    replies = relationship("EventComment", back_populates="parent")
    parent = relationship("EventComment", back_populates="replies", remote_side=[id])

    def __repr__(self):
        kind = "reply" if self.parent_id else "top"
        return f"<EventComment id={self.id} event={self.event_id} {kind}>"


class CommentVote(Base):
    """One user's vote on one comment.

    The unique constraint is what enforces one-vote-per-user — in the database,
    not in application logic that two concurrent requests could race past.
    Switching a like to a dislike is an UPDATE of `value`, not a second row.
    """
    __tablename__ = "comment_votes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_votes_one_per_user"),
    )

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("event_comments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    value = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class FighterBio(Base):
    """An LLM-written summary of one fighter's career.

    Cached on `fights_at_generation`, not on a timestamp. A fighter's record only
    changes when they fight, so that number IS the cache key: equal means the
    text is still true, different means regenerate. Time-based expiry would burn
    quota rewriting identical prose about someone who last fought in 2019.
    """
    __tablename__ = "fighter_bios"

    id = Column(Integer, primary_key=True)
    # Normalized, because the two data sources spell names differently
    # (accents) and a lookup must not miss its own cache entry.
    fighter_norm = Column(String, unique=True, nullable=False, index=True)
    fighter = Column(String, nullable=False)       # display spelling
    body = Column(String, nullable=False)

    fights_at_generation = Column(Integer, nullable=False)
    model = Column(String, nullable=False)         # which model wrote it
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
