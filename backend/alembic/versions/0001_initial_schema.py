"""initial schema: postgis extension, trails, wildlife_sightings

Revision ID: 0001
Revises:
Create Date: 2026-06-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Geometry columns get a GIST index auto-created by GeoAlchemy2's DDL hook
    # (spatial_index=True is the default), so no explicit op.create_index for `geom` here.
    op.create_table(
        "trails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("features", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("length_m", sa.Float(), nullable=True),
        sa.Column("geom", Geometry(geometry_type="LINESTRING", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "wildlife_sightings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="ebird"),
        sa.Column("species_code", sa.String(20), nullable=False),
        sa.Column("common_name", sa.String(200), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checklist_id", sa.String(50), nullable=True),
        sa.Column("is_obscured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_wildlife_sightings_species_code", "wildlife_sightings", ["species_code"]
    )


def downgrade() -> None:
    op.drop_table("wildlife_sightings")
    op.drop_table("trails")
    # Deliberately not dropping the postgis extension: it requires superuser/ownership
    # privileges a normal app DB role won't have, and other schemas may depend on it.
