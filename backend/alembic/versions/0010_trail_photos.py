"""trail_photos: rider-supplied hero photo per catalog trail

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trail_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trail_external_id", sa.String(length=50), nullable=False),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=60), nullable=False, server_default="image/jpeg"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_trail_photos_trail_external_id",
        "trail_photos",
        ["trail_external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_trail_photos_trail_external_id", table_name="trail_photos")
    op.drop_table("trail_photos")
