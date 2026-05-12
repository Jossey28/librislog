"""drop apikey is_primary

Revision ID: aa12bb34cc56
Revises: f1e2d3c4b5a6
Create Date: 2026-05-12 12:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "aa12bb34cc56"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_apikey_is_primary", table_name="apikey")
    op.drop_column("apikey", "is_primary")


def downgrade() -> None:
    op.add_column(
        "apikey",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_apikey_is_primary", "apikey", ["is_primary"], unique=False)
