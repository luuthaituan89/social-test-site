"""Add user account lifecycle state.

Revision ID: 0003_user_data_lifecycle
Revises: 0002_advanced_privacy
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_user_data_lifecycle"
down_revision = "0002_advanced_privacy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("account_status", sa.String(30), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("deactivated_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("deletion_requested_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("deletion_scheduled_for", sa.DateTime(), nullable=True))
    op.create_index("ix_users_account_status", "users", ["account_status"])
    op.create_index("ix_users_deletion_scheduled_for", "users", ["deletion_scheduled_for"])


def downgrade() -> None:
    op.drop_index("ix_users_deletion_scheduled_for", table_name="users")
    op.drop_index("ix_users_account_status", table_name="users")
    op.drop_column("users", "deletion_scheduled_for")
    op.drop_column("users", "deletion_requested_at")
    op.drop_column("users", "deactivated_at")
    op.drop_column("users", "account_status")
