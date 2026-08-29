"""Add account sessions, recovery tokens and TOTP security.

Revision ID: 0004_account_security
Revises: 0003_user_data_lifecycle
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_account_security"
down_revision = "0003_user_data_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if inspect(op.get_bind()).has_table("auth_sessions"):
        return
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("totp_secret_encrypted", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("recovery_codes", sa.Text(), nullable=True))
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("previous_token_hash", sa.String(64), nullable=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("device_name", sa.String(160), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.String(80), nullable=True),
    )
    for name, cols, unique in [
        ("ix_auth_sessions_public_id", ["public_id"], True),
        ("ix_auth_sessions_user_id", ["user_id"], False),
        ("ix_auth_sessions_refresh_token_hash", ["refresh_token_hash"], True),
        ("ix_auth_sessions_previous_token_hash", ["previous_token_hash"], False),
        ("ix_auth_sessions_device_id", ["device_id"], False),
        ("ix_auth_sessions_last_seen_at", ["last_seen_at"], False),
        ("ix_auth_sessions_expires_at", ["expires_at"], False),
        ("ix_auth_sessions_revoked_at", ["revoked_at"], False),
    ]: op.create_index(name, "auth_sessions", cols, unique=unique)
    op.create_table(
        "account_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_account_tokens_user_id", "account_tokens", ["user_id"])
    op.create_index("ix_account_tokens_purpose", "account_tokens", ["purpose"])
    op.create_index("ix_account_tokens_token_hash", "account_tokens", ["token_hash"], unique=True)
    op.create_index("ix_account_tokens_expires_at", "account_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_table("account_tokens")
    op.drop_table("auth_sessions")
    for column in ("recovery_codes", "totp_secret_encrypted", "totp_enabled", "auth_version", "email_verified_at"):
        op.drop_column("users", column)
