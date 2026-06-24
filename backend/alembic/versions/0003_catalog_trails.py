"""catalog_trails: the broad TrailAPI catalog (point + metadata)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-24

A POINT-geometry table separate from `trails`, holding the on-demand-cached TrailAPI
dataset. See app/models/catalog_trail.py.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # The POINT geom column gets its GIST index auto-created by GeoAlchemy2's DDL hook.
    op.create_table(
        "catalog_trails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="trailapi"),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("difficulty", sa.String(40), nullable=True),
        sa.Column("length_mi", sa.Float(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("region", sa.String(120), nullable=True),
        sa.Column("country", sa.String(120), nullable=True),
        sa.Column("url", sa.String(400), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_catalog_trails_external_id", "catalog_trails", ["external_id"])
    op.create_index("ix_catalog_trails_external_id", "catalog_trails", ["external_id"])


def downgrade() -> None:
    op.drop_table("catalog_trails")
