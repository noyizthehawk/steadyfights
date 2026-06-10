"""
Database models. Each class here maps to one table.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from .database import Base


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
