"""migrate date_started and date_finished to datetime

Revision ID: a31c9e2f7b44
Revises: 8b0d7f6c9f31
Create Date: 2026-05-11 12:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a31c9e2f7b44'
down_revision: Union[str, Sequence[str], None] = '8b0d7f6c9f31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('book') as batch_op:
        batch_op.drop_index(op.f('ix_book_date_started'))
        batch_op.drop_index(op.f('ix_book_date_finished'))

    op.add_column('book', sa.Column('date_started_tmp', sa.DateTime(), nullable=True))
    op.add_column('book', sa.Column('date_finished_tmp', sa.DateTime(), nullable=True))

    op.execute(
        """
        UPDATE book
        SET date_started_tmp = CASE
            WHEN date_started IS NOT NULL THEN date_started || ' 00:00:00'
            ELSE NULL
        END
        """
    )
    op.execute(
        """
        UPDATE book
        SET date_finished_tmp = CASE
            WHEN date_finished IS NOT NULL THEN date_finished || ' 00:00:00'
            ELSE NULL
        END
        """
    )

    with op.batch_alter_table('book') as batch_op:
        batch_op.drop_column('date_started')
        batch_op.drop_column('date_finished')

    op.alter_column('book', 'date_started_tmp', new_column_name='date_started')
    op.alter_column('book', 'date_finished_tmp', new_column_name='date_finished')

    op.create_index(op.f('ix_book_date_started'), 'book', ['date_started'], unique=False)
    op.create_index(op.f('ix_book_date_finished'), 'book', ['date_finished'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_book_date_finished'), table_name='book')
    op.drop_index(op.f('ix_book_date_started'), table_name='book')

    op.add_column('book', sa.Column('date_started_tmp', sa.Date(), nullable=True))
    op.add_column('book', sa.Column('date_finished_tmp', sa.Date(), nullable=True))

    op.execute(
        """
        UPDATE book
        SET date_started_tmp = CASE
            WHEN date_started IS NOT NULL THEN DATE(date_started)
            ELSE NULL
        END
        """
    )
    op.execute(
        """
        UPDATE book
        SET date_finished_tmp = CASE
            WHEN date_finished IS NOT NULL THEN DATE(date_finished)
            ELSE NULL
        END
        """
    )

    with op.batch_alter_table('book') as batch_op:
        batch_op.drop_column('date_started')
        batch_op.drop_column('date_finished')

    op.alter_column('book', 'date_started_tmp', new_column_name='date_started')
    op.alter_column('book', 'date_finished_tmp', new_column_name='date_finished')

    op.create_index(op.f('ix_book_date_started'), 'book', ['date_started'], unique=False)
    op.create_index(op.f('ix_book_date_finished'), 'book', ['date_finished'], unique=False)
