"""trips: logged rides with species seen

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trail_external_id", sa.String(length=50), nullable=True),
        sa.Column("trail_name", sa.String(length=200), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=True),
        sa.Column("miles", sa.Float(), nullable=True),
        sa.Column("ridden_on", sa.Date(), nullable=False),
        sa.Column("birds", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trips_trail_external_id"), "trips", ["trail_external_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_trips_trail_external_id"), table_name="trips")
    op.drop_table("trips")
