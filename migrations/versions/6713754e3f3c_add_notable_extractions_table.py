"""add notable_extractions table

Revision ID: 6713754e3f3c
Revises: 1f7aa2e58a0f
Create Date: 2026-08-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6713754e3f3c'
down_revision: Union[str, Sequence[str], None] = '1f7aa2e58a0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remembers which YouTube video a notable user's picks for an event came from.
    # One row per (user, event) — the unique constraint lets the AI pipeline upsert.
    op.create_table(
        'notable_extractions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['event_id'], ['ufc_events.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'event_id', name='uq_notable_extraction'),
    )
    op.create_index(op.f('ix_notable_extractions_user_id'), 'notable_extractions', ['user_id'])
    op.create_index(op.f('ix_notable_extractions_event_id'), 'notable_extractions', ['event_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_notable_extractions_event_id'), table_name='notable_extractions')
    op.drop_index(op.f('ix_notable_extractions_user_id'), table_name='notable_extractions')
    op.drop_table('notable_extractions')
