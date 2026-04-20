"""Split approval and reception operational roles.

Revision ID: 20260420_0009
Revises: 20260420_0008
Create Date: 2026-04-20
"""

from __future__ import annotations

from alembic import op

revision = "20260420_0009"
down_revision = "20260420_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('employee','fleet_approver','fleet_reception','fleet_admin')",
    )


def downgrade() -> None:
    op.execute("UPDATE users SET role='employee' WHERE role IN ('fleet_approver','fleet_reception')")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('employee','fleet_admin')",
    )
