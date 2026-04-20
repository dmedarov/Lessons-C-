"""Add car assignment trace table.

Revision ID: 20260420_0008
Revises: 20260420_0007
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0008"
down_revision = "20260420_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "car_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reservation_id", sa.Integer(), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("car_id", sa.Integer(), sa.ForeignKey("cars.id"), nullable=False),
        sa.Column("assignment_mode", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "assignment_mode IN ('manual','quick_book','suggested','auto')",
            name="ck_car_assignments_assignment_mode",
        ),
    )
    op.create_index(
        "idx_car_assignments_reservation",
        "car_assignments",
        ["reservation_id"],
    )
    op.create_index(
        "idx_car_assignments_car_created",
        "car_assignments",
        ["car_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_car_assignments_car_created", table_name="car_assignments")
    op.drop_index("idx_car_assignments_reservation", table_name="car_assignments")
    op.drop_table("car_assignments")
