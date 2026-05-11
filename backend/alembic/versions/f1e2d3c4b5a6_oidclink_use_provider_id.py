"""oidclink use provider_id

Revision ID: f1e2d3c4b5a6
Revises: c3f4d7a9b2e1
Create Date: 2026-05-11 23:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.config import settings


revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, Sequence[str], None] = "c3f4d7a9b2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("oidclink") as batch_op:
        batch_op.add_column(sa.Column("provider_id", sa.String(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE oidclink SET provider_id = :provider_id WHERE provider_id IS NULL"),
        {"provider_id": settings.oidc_provider_id},
    )

    with op.batch_alter_table("oidclink") as batch_op:
        batch_op.alter_column("provider_id", existing_type=sa.String(), nullable=False)
        batch_op.create_index(op.f("ix_oidclink_provider_id"), ["provider_id"], unique=False)
        batch_op.drop_index(op.f("ix_oidclink_provider_name"))
        batch_op.drop_column("provider_name")


def downgrade() -> None:
    with op.batch_alter_table("oidclink") as batch_op:
        batch_op.add_column(sa.Column("provider_name", sa.String(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE oidclink SET provider_name = :provider_name WHERE provider_name IS NULL"),
        {"provider_name": settings.oidc_provider_name},
    )

    with op.batch_alter_table("oidclink") as batch_op:
        batch_op.alter_column("provider_name", existing_type=sa.String(), nullable=False)
        batch_op.create_index(op.f("ix_oidclink_provider_name"), ["provider_name"], unique=False)
        batch_op.drop_index(op.f("ix_oidclink_provider_id"))
        batch_op.drop_column("provider_id")
