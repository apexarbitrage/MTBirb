"""wildlife_sightings: add is_notable flag for eBird notable observations

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wildlife_sightings",
        sa.Column("is_notable", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("wildlife_sightings", "is_notable")
