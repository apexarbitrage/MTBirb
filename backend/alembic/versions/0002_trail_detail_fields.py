"""trail detail fields: slug, ride attributes, and derived overlay

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-23

Adds the trail-intrinsic ride attributes the UI needs plus a `derived` JSON overlay for
the wildlife/weather presentation fields (seeded placeholders until eBird/NWS replace
them). See app/models/trail.py.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trails", sa.Column("slug", sa.String(60), nullable=True))
    op.create_unique_constraint("uq_trails_slug", "trails", ["slug"])

    op.add_column("trails", sa.Column("miles", sa.Float(), nullable=True))
    op.add_column("trails", sa.Column("effort", sa.Float(), nullable=True))
    op.add_column("trails", sa.Column("ride_time_min", sa.Integer(), nullable=True))
    op.add_column("trails", sa.Column("location", sa.String(200), nullable=True))
    op.add_column("trails", sa.Column("gain_ft", sa.Integer(), nullable=True))
    op.add_column("trails", sa.Column("climb_ft", sa.Integer(), nullable=True))
    op.add_column("trails", sa.Column("descent_ft", sa.Integer(), nullable=True))
    op.add_column("trails", sa.Column("avg_up_grade", sa.String(10), nullable=True))
    op.add_column("trails", sa.Column("avg_down_grade", sa.String(10), nullable=True))
    op.add_column("trails", sa.Column("elevation", sa.JSON(), nullable=True))
    op.add_column("trails", sa.Column("derived", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("trails", "derived")
    op.drop_column("trails", "elevation")
    op.drop_column("trails", "avg_down_grade")
    op.drop_column("trails", "avg_up_grade")
    op.drop_column("trails", "descent_ft")
    op.drop_column("trails", "climb_ft")
    op.drop_column("trails", "gain_ft")
    op.drop_column("trails", "location")
    op.drop_column("trails", "ride_time_min")
    op.drop_column("trails", "effort")
    op.drop_column("trails", "miles")
    op.drop_constraint("uq_trails_slug", "trails", type_="unique")
    op.drop_column("trails", "slug")
