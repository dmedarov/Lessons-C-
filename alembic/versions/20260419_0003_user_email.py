"""add email to users

Revision ID: 20260419_0003
Revises: 20260418_0002
Create Date: 2026-04-19 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260419_0003"
down_revision = "20260418_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email")
