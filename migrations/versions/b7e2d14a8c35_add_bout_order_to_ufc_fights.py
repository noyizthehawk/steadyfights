"""add bout_order and card_section to ufc_fights

Revision ID: b7e2d14a8c35
Revises: a3f1c07d9b42
Create Date: 2026-09-12 03:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2d14a8c35'
down_revision: Union[str, Sequence[str], None] = 'a3f1c07d9b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add card position to fights.

    ufc.com lists bouts in card order — main event first, opener last — and the
    scraper was discarding that index. Ordering therefore fell back to primary
    key, which matches card order only by accident: it holds for a card scraped
    once and never changed, and breaks the moment a replacement bout is added,
    because the new row gets the highest id and sorts below the opener.

    Both columns are nullable with no backfill. Every existing row stays NULL,
    and queries order by (bout_order IS NULL, bout_order, id) so untouched
    events keep exactly the order they have today. Rows fill in as the scraper
    next visits each event.
    """
    op.add_column("ufc_fights", sa.Column("bout_order", sa.Integer(), nullable=True))
    op.add_column("ufc_fights", sa.Column("card_section", sa.String(), nullable=True))


def downgrade() -> None:
    """Drop card position. Ordering reverts to primary key, which puts any
    late-added bout at the bottom of the card."""
    op.drop_column("ufc_fights", "card_section")
    op.drop_column("ufc_fights", "bout_order")
