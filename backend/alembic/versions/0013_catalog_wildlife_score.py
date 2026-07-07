"""catalog_trails: add precomputed wildlife_score (JSONB)

The trail list scored wildlife live on every request (score_catalog_trails runs an ST_DWithin
spatial join over wildlife_sightings per load). Migration 0012's geography index made that join
use an index, but it's still per-request work that grows with the cache. This column stores the
(trimmed) score dict on the row so the list reads it as a plain column - refreshed on sync/seed
and lazily for any never-scored row (see services/wildlife_likelihood.refresh_catalog_scores).

JSONB (not JSON) so the value is stored decomposed - no reason to keep the raw text, and it's the
right default for a computed blob we only ever read whole.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catalog_trails",
        sa.Column("wildlife_score", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catalog_trails", "wildlife_score")
