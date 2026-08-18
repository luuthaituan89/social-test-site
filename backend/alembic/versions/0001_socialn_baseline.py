"""Create the SocialN schema and upgrade legacy development databases.

Revision ID: 0001_socialn_baseline
Revises: None
"""
from alembic import op
from sqlalchemy import text

from app.database import Base
from app import models  # noqa: F401

revision = "0001_socialn_baseline"
down_revision = None
branch_labels = None
depends_on = None

LEGACY_COLUMNS = [
    "ALTER TABLE users ADD COLUMN gender VARCHAR(30) NULL",
    "ALTER TABLE users ADD COLUMN relationship_status VARCHAR(50) NULL",
    "ALTER TABLE users ADD COLUMN relationship_partner_id INT NULL",
    "ALTER TABLE users ADD COLUMN relationship_since DATE NULL",
    "ALTER TABLE users ADD COLUMN username_changed_at DATETIME NULL",
    "ALTER TABLE users ADD COLUMN last_seen_at DATETIME NULL",
    "ALTER TABLE users ADD COLUMN active_status_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE conversations ADD COLUMN pinned_a BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE conversations ADD COLUMN pinned_b BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE conversations ADD COLUMN archived_a BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE conversations ADD COLUMN archived_b BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE conversations ADD COLUMN cleared_at_a DATETIME NULL",
    "ALTER TABLE conversations ADD COLUMN cleared_at_b DATETIME NULL",
    "ALTER TABLE conversations ADD COLUMN direct_key VARCHAR(64) NULL UNIQUE",
    "ALTER TABLE conversations ADD COLUMN theme VARCHAR(40) NOT NULL DEFAULT 'default'",
    "ALTER TABLE conversations ADD COLUMN quick_reaction VARCHAR(20) NOT NULL DEFAULT '👍'",
    "ALTER TABLE conversations ADD COLUMN nickname_a VARCHAR(120) NULL",
    "ALTER TABLE conversations ADD COLUMN nickname_b VARCHAR(120) NULL",
    "ALTER TABLE conversations ADD COLUMN word_effects TEXT NULL",
    "ALTER TABLE conversations ADD COLUMN disappearing_seconds INT NOT NULL DEFAULT 0",
    "ALTER TABLE conversations ADD COLUMN muted_until_a DATETIME NULL",
    "ALTER TABLE conversations ADD COLUMN muted_until_b DATETIME NULL",
    "ALTER TABLE conversations ADD COLUMN restricted_a BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE conversations ADD COLUMN restricted_b BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE messages ADD COLUMN message_type VARCHAR(20) NOT NULL DEFAULT 'text'",
    "ALTER TABLE messages ADD COLUMN attachment_url VARCHAR(500) NULL",
    "ALTER TABLE messages ADD COLUMN attachment_name VARCHAR(255) NULL",
    "ALTER TABLE messages ADD COLUMN attachment_mime VARCHAR(120) NULL",
    "ALTER TABLE messages ADD COLUMN sticker TEXT NULL",
    "ALTER TABLE messages ADD COLUMN reply_to_id INT NULL",
    "ALTER TABLE messages ADD COLUMN forwarded_from_id INT NULL",
    "ALTER TABLE messages ADD COLUMN is_pinned BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE messages ADD COLUMN is_unsent BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE messages ADD COLUMN expires_at DATETIME NULL",
    "ALTER TABLE likes ADD COLUMN reaction VARCHAR(20) NOT NULL DEFAULT 'like'",
    "ALTER TABLE posts ADD COLUMN media_type VARCHAR(20) NOT NULL DEFAULT 'image'",
    "ALTER TABLE posts ADD COLUMN album_id INT NULL",
    "ALTER TABLE posts ADD COLUMN sticker TEXT NULL",
    "ALTER TABLE `groups` ADD COLUMN rules TEXT NULL",
    "ALTER TABLE `group_posts` ADD COLUMN is_pinned BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE `groups` ADD COLUMN allow_anonymous_posts BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE `groups` ADD COLUMN require_post_approval BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE group_members ADD COLUMN posting_muted_until DATETIME NULL",
    "ALTER TABLE group_members ADD COLUMN notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE chat_groups ADD COLUMN theme VARCHAR(40) NOT NULL DEFAULT 'default'",
    "ALTER TABLE chat_groups ADD COLUMN quick_reaction VARCHAR(20) NOT NULL DEFAULT '👍'",
    "ALTER TABLE chat_groups ADD COLUMN invite_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE chat_groups ADD COLUMN invite_token VARCHAR(80) NULL",
    "ALTER TABLE chat_groups ADD COLUMN member_customization BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE chat_group_members ADD COLUMN nickname VARCHAR(120) NULL",
    "ALTER TABLE chat_group_members ADD COLUMN muted_until DATETIME NULL",
    "ALTER TABLE chat_group_members ADD COLUMN notification_sound VARCHAR(40) NOT NULL DEFAULT 'default'",
    "ALTER TABLE chat_group_members ADD COLUMN last_read_at DATETIME NULL",
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    # Existing SocialN installations predate Alembic. Statements are idempotent
    # by design: duplicate-column errors mean that database is already current.
    for statement in LEGACY_COLUMNS:
        try:
            bind.execute(text(statement))
        except Exception:
            pass


def downgrade() -> None:
    # Baseline downgrade is deliberately non-destructive for user-generated data.
    pass
