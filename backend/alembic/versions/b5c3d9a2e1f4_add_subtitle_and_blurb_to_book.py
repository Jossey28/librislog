"""add subtitle and blurb to book

Revision ID: b5c3d9a2e1f4
Revises: f4c2b8a1d9e3
Create Date: 2026-05-19 10:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5c3d9a2e1f4"
down_revision: Union[str, Sequence[str], None] = "a9c1d0e5f2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.add_column(sa.Column("subtitle", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("blurb", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.drop_column("blurb")
        batch_op.drop_column("subtitle")
