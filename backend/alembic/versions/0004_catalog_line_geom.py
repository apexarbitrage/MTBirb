"""catalog_trails: add line_geom for OSM-matched ridable lines

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # The geometry column's GIST index is created automatically by GeoAlchemy2's add_column hook.
    op.add_column(
        "catalog_trails",
        sa.Column("line_geom", Geometry(geometry_type="LINESTRING", srid=4326), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catalog_trails", "line_geom")
