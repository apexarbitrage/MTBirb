"""wildlife_sightings: composite index on (species_code, observed_at)

`species_seasonality` - called by nearly every wildlife query (the species picker, catalog
scoring, per-species ranking) - filters `species_code IN (...) AND observed_at < cutoff` with
potentially 100+ codes. With no index on species_code that's a sequential scan of the whole
sightings table on every call, which after multi-region seeding takes tens of seconds; being a
*synchronous* query inside an async endpoint, it also freezes the event loop for the duration
(starving /health and getting the container restarted - the 502 bursts). The composite index
serves the IN + range filter directly.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_wildlife_sightings_species_observed "
        "ON wildlife_sightings (species_code, observed_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_wildlife_sightings_species_observed")
