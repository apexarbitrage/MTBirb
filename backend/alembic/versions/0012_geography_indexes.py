"""functional GiST indexes on the geography casts (spatial-join performance)

The wildlife scorer / species picker / per-species ranking all filter with
ST_DWithin / ST_Intersects on `geom::geography` (see services/wildlife_likelihood.py).
GeoAlchemy2's auto GiST index is on the *geometry* column, which the planner can't use for a
geography-cast predicate - so those queries sequentially scan wildlife_sightings on every request,
and get slower as the cache grows. These functional indexes match the geography cast so the join
uses an index instead. (This is NOT the redundant-geometry-index case CLAUDE.md warns about - the
auto index is on geometry, these are on the geography expression.)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


# (index name, table, geometry column). The big one is wildlife_sightings - it grows unbounded as
# areas are seeded/browsed and is scanned by every catalog scoring query.
_INDEXES = [
    ("ix_wildlife_sightings_geom_geog", "wildlife_sightings", "geom"),
    ("ix_catalog_trails_geom_geog", "catalog_trails", "geom"),
    ("ix_catalog_trails_line_geom_geog", "catalog_trails", "line_geom"),
]


def upgrade() -> None:
    for name, table, col in _INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING gist (({col}::geography))"
        )


def downgrade() -> None:
    for name, _table, _col in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
