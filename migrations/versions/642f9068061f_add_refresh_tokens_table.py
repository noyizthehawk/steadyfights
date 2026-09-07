"""add refresh_tokens table

Revision ID: 642f9068061f
Revises: 6713754e3f3c
Create Date: 2026-09-07 00:39:13.372120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '642f9068061f'
down_revision: Union[str, Sequence[str], None] = '6713754e3f3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create refresh_tokens.

    Hand-written: the app's startup calls Base.metadata.create_all(), which had
    already created this table locally, so --autogenerate saw no difference and
    emitted an empty upgrade(). The table still needs recording here or a fresh
    database built from `alembic upgrade head` would not have it.
    """
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        # self-referencing: each row points at the token that superseded it
        sa.ForeignKeyConstraint(["replaced_by"], ["refresh_tokens.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # unique AND indexed: every refresh is a lookup by this column
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    # not unique: a family has many rows, and revoking one revokes them all
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"], unique=False)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop refresh_tokens. Everyone gets logged out — the sessions live here."""
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
