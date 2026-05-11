"""add indexes for date_started and date_finished

Revision ID: 8b0d7f6c9f31
Revises: 4d8b9a2c1e6f
Create Date: 2026-05-11 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8b0d7f6c9f31'
down_revision: Union[str, Sequence[str], None] = '4d8b9a2c1e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_book_date_started'), 'book', ['date_started'], unique=False)
    op.create_index(op.f('ix_book_date_finished'), 'book', ['date_finished'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_book_date_finished'), table_name='book')
    op.drop_index(op.f('ix_book_date_started'), table_name='book')
