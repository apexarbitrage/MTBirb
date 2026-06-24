"""trips: add geotagged photos (thumbnail + GPS)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trips", sa.Column("photos", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("trips", "photos")
