"""trail_routes: saved multi-trail routes; trips: optional route link

A TrailRoute is an ordered chain of catalog trails a rider linked together in the route builder.
Only the name + ordered member external_ids are stored - the line, stats, and wildlife overlay are
recomputed from the member trails at read time, so a route keeps improving as its members' metrics
refine (and there's no geometry column to keep in sync). No FKs, matching trips' loose coupling.

trips.route_id links a logged ride to the route it was ridden on - nullable and FK-less on purpose,
so deleting a route never touches ride history (the trip carries the route name in trail_name).

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trail_routes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("trail_external_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("trips", sa.Column("route_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("trips", "route_id")
    op.drop_table("trail_routes")
