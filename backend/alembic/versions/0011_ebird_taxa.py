"""ebird_taxa: cached eBird species taxonomy, for name search

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ebird_taxa",
        sa.Column("species_code", sa.String(length=20), primary_key=True),
        sa.Column("common_name", sa.String(length=200), nullable=False),
        sa.Column("scientific_name", sa.String(length=200), nullable=False),
    )
    op.create_index("ix_ebird_taxa_common_name", "ebird_taxa", ["common_name"])


def downgrade() -> None:
    op.drop_index("ix_ebird_taxa_common_name", table_name="ebird_taxa")
    op.drop_table("ebird_taxa")
