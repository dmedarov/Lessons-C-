"""initial schema

Revision ID: 20260418_0001
Revises:
Create Date: 2026-04-18 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260418_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("role IN ('employee','fleet_admin')", name="ck_users_role"),
        sa.CheckConstraint("active IN (0,1)", name="ck_users_active"),
    )

    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate_number", sa.Text(), nullable=False, unique=True),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("active IN (0,1)", name="ck_cars_active"),
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("car_id", sa.Integer(), sa.ForeignKey("cars.id"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("employee_name", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Text(), nullable=False),
        sa.Column("end_time", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("checked_out_at", sa.Text(), nullable=True),
        sa.Column("returned_at", sa.Text(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','cancelled')",
            name="ck_reservations_status",
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reservation_id", sa.Integer(), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("at", sa.Text(), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("reservation_id", sa.Integer(), sa.ForeignKey("reservations.id"), nullable=True),
        sa.Column("read_at", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_index("idx_reservations_car_time", "reservations", ["car_id", "start_time", "end_time"])
    op.create_index("idx_reservations_status", "reservations", ["status"])
    op.create_index("idx_audit_reservation", "audit_log", ["reservation_id"])
    op.create_index("idx_notifications_user_created", "notifications", ["user_id", "created_at"])
    op.create_index("idx_notifications_user_read", "notifications", ["user_id", "read_at"])


def downgrade() -> None:
    op.drop_index("idx_notifications_user_read", table_name="notifications")
    op.drop_index("idx_notifications_user_created", table_name="notifications")
    op.drop_index("idx_audit_reservation", table_name="audit_log")
    op.drop_index("idx_reservations_status", table_name="reservations")
    op.drop_index("idx_reservations_car_time", table_name="reservations")
    op.drop_table("notifications")
    op.drop_table("audit_log")
    op.drop_table("reservations")
    op.drop_table("cars")
    op.drop_table("users")
