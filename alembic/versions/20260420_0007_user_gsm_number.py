"""Add GSM number to users.

Revision ID: 20260420_0007
Revises: 20260420_0006
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0007"
down_revision = "20260420_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gsm_number", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gsm_number")
