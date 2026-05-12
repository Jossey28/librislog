"""rename genre to tags

Revision ID: b7a4d2e9c1f0
Revises: aa12bb34cc56
Create Date: 2026-05-12 14:15:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b7a4d2e9c1f0"
down_revision = "aa12bb34cc56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.alter_column("genre", new_column_name="tags")


def downgrade() -> None:
    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.alter_column("tags", new_column_name="genre")
