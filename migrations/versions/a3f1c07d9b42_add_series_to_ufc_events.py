"""add series to ufc_events

Revision ID: a3f1c07d9b42
Revises: dea0495724b0
Create Date: 2026-09-12 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1c07d9b42'
down_revision: Union[str, Sequence[str], None] = 'dea0495724b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ufc_events.series — the card's brand line from ufc.com's hero prefix
    ("Noche UFC", "Crypto.com UFC 331", "UFC 332", or a generic "UFC Fight
    Night").

    `title` only ever holds the matchup ("Silva vs Delgado"), so for a card with
    no number in its name there was nothing anywhere identifying WHICH event it
    was. Video matching fell back to shared surnames, and a "Medic vs Rodriguez
    — UFC Belgrade" video won a Noche UFC pairing on the single common name
    "rodriguez".

    nullable, no server_default: existing rows genuinely don't know their brand
    and NULL says so honestly. The scraper fills it on the next run, and the
    matcher treats an empty series as "no brand signal" rather than a match.
    """
    op.add_column("ufc_events", sa.Column("series", sa.String(), nullable=True))


def downgrade() -> None:
    """Drop series. Unnumbered cards lose their only identifier again, so video
    matching for them falls back to surname overlap."""
    op.drop_column("ufc_events", "series")
