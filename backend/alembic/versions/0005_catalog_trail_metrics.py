"""catalog_trails: add DEM-derived terrain metrics

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("catalog_trails", sa.Column("metric_length_mi", sa.Float(), nullable=True))
    op.add_column("catalog_trails", sa.Column("ascent_ft", sa.Integer(), nullable=True))
    op.add_column("catalog_trails", sa.Column("descent_ft", sa.Integer(), nullable=True))
    op.add_column("catalog_trails", sa.Column("avg_up_grade", sa.String(length=12), nullable=True))
    op.add_column("catalog_trails", sa.Column("avg_down_grade", sa.String(length=12), nullable=True))
    op.add_column("catalog_trails", sa.Column("elevation_profile", sa.JSON(), nullable=True))
    op.add_column("catalog_trails", sa.Column("ride_time_min", sa.Integer(), nullable=True))
    op.add_column("catalog_trails", sa.Column("effort", sa.Float(), nullable=True))
    op.add_column("catalog_trails", sa.Column("elev_source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("catalog_trails", "elev_source")
    op.drop_column("catalog_trails", "effort")
    op.drop_column("catalog_trails", "ride_time_min")
    op.drop_column("catalog_trails", "elevation_profile")
    op.drop_column("catalog_trails", "avg_down_grade")
    op.drop_column("catalog_trails", "avg_up_grade")
    op.drop_column("catalog_trails", "descent_ft")
    op.drop_column("catalog_trails", "ascent_ft")
    op.drop_column("catalog_trails", "metric_length_mi")
