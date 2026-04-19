"""Add notes column to cars table.

Revision ID: 20260419_0004
Revises: 20260419_0003
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260419_0004"
down_revision = "20260419_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cars", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cars", "notes")
