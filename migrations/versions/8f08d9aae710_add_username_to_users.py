"""add username to users

Revision ID: 8f08d9aae710
Revises: 45b7f3f2dfde
Create Date: 2026-07-25 23:17:45.686529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f08d9aae710'
down_revision: Union[str, Sequence[str], None] = '45b7f3f2dfde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a required, case-insensitively-unique username to users."""
    # 1. Add as NULLABLE first. Existing rows have no username, so adding it as
    #    NOT NULL straight away would be rejected on those rows.
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))

    # 2. Backfill every existing user with a placeholder (user<id>) they can
    #    change later. Done through the bound connection with SQLAlchemy Core so
    #    it behaves identically on SQLite (local) and Postgres (prod) — raw string
    #    concatenation syntax differs between the two.
    conn = op.get_bind()
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("username", sa.String))
    rows = conn.execute(sa.select(users.c.id).where(users.c.username.is_(None))).fetchall()
    for (uid,) in rows:
        conn.execute(users.update().where(users.c.id == uid).values(username=f"user{uid}"))

    # 3. Now that every row has a value, enforce NOT NULL. batch_alter_table is
    #    the cross-dialect way: a normal ALTER on Postgres, a table-rebuild on
    #    SQLite (which cannot ALTER COLUMN directly).
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", existing_type=sa.String(), nullable=False)

    # 4. Case-insensitive uniqueness via a functional index on lower(username),
    #    matching the Index declared on the User model.
    op.create_index("uq_users_username_lower", "users", [sa.text("lower(username)")], unique=True)


def downgrade() -> None:
    """Reverse the username addition."""
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_column("users", "username")
