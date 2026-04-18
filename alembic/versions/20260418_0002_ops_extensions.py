"""operations extensions

Revision ID: 20260418_0002
Revises: 20260418_0001
Create Date: 2026-04-18 15:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260418_0002"
down_revision = "20260418_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notification_id", sa.Integer(), sa.ForeignKey("notifications.id"), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_notification_deliveries_notification",
        "notification_deliveries",
        ["notification_id", "delivered_at"],
    )

    op.create_table(
        "user_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("at", sa.Text(), nullable=False),
    )
    op.create_index("idx_user_audit_target", "user_audit_log", ["target_user_id", "at"])

    op.create_table(
        "car_blackouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("car_id", sa.Integer(), sa.ForeignKey("cars.id"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Text(), nullable=False),
        sa.Column("end_time", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("kind IN ('service','maintenance','inspection','blocked')", name="ck_blackouts_kind"),
        sa.CheckConstraint("active IN (0,1)", name="ck_blackouts_active"),
    )
    op.create_index("idx_blackouts_car_time", "car_blackouts", ["car_id", "start_time", "end_time"])


def downgrade() -> None:
    op.drop_index("idx_blackouts_car_time", table_name="car_blackouts")
    op.drop_table("car_blackouts")
    op.drop_index("idx_user_audit_target", table_name="user_audit_log")
    op.drop_table("user_audit_log")
    op.drop_index("idx_notification_deliveries_notification", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
