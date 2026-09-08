"""add status to ufc_fights

Revision ID: dea0495724b0
Revises: 642f9068061f
Create Date: 2026-09-08 01:16:15.987367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dea0495724b0'
down_revision: Union[str, Sequence[str], None] = '642f9068061f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ufc_fights.status and backfill it from data we already have.

    server_default rather than a plain default: existing rows need a value at
    ALTER time, and SQLite can't add a NOT NULL column without one.
    """
    op.add_column(
        "ufc_fights",
        sa.Column("status", sa.String(), nullable=False, server_default="scheduled"),
    )
    op.create_index("ix_ufc_fights_status", "ufc_fights", ["status"])
    # anything with a winner already happened; everything else stays 'scheduled'.
    # Cancelled bouts can't be identified retroactively — the scraper marks those
    # from now on, when a matchup disappears from an event's card.
    op.execute("UPDATE ufc_fights SET status = 'completed' WHERE winner IS NOT NULL")


def downgrade() -> None:
    """Drop status. The scheduled/cancelled distinction is lost — winner IS NULL
    goes back to meaning three different things at once."""
    op.drop_index("ix_ufc_fights_status", table_name="ufc_fights")
    op.drop_column("ufc_fights", "status")
