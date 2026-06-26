"""catalog_trails: add expanded terrain + surface stats

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("catalog_trails", sa.Column("max_grade", sa.String(length=12), nullable=True))
    op.add_column("catalog_trails", sa.Column("high_point_ft", sa.Integer(), nullable=True))
    op.add_column("catalog_trails", sa.Column("low_point_ft", sa.Integer(), nullable=True))
    op.add_column("catalog_trails", sa.Column("longest_climb_mi", sa.Float(), nullable=True))
    op.add_column("catalog_trails", sa.Column("aspect", sa.String(length=4), nullable=True))
    op.add_column("catalog_trails", sa.Column("sun_exposure", sa.Float(), nullable=True))
    op.add_column("catalog_trails", sa.Column("surface", sa.String(length=40), nullable=True))
    op.add_column("catalog_trails", sa.Column("mtb_scale", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("catalog_trails", "mtb_scale")
    op.drop_column("catalog_trails", "surface")
    op.drop_column("catalog_trails", "sun_exposure")
    op.drop_column("catalog_trails", "aspect")
    op.drop_column("catalog_trails", "longest_climb_mi")
    op.drop_column("catalog_trails", "low_point_ft")
    op.drop_column("catalog_trails", "high_point_ft")
    op.drop_column("catalog_trails", "max_grade")
