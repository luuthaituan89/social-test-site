"""Add composite indexes for feed, chat, notifications and group timelines.

Revision ID: 0007_query_indexes
Revises: 0006_engagement_platform
"""
from alembic import op
from sqlalchemy import inspect

revision = "0007_query_indexes"
down_revision = "0006_engagement_platform"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_posts_author_created", "posts", ["author_id", "created_at"]),
    ("ix_likes_post_created", "likes", ["post_id", "created_at"]),
    ("ix_comments_post_created", "comments", ["post_id", "created_at"]),
    ("ix_messages_conversation_id_desc", "messages", ["conversation_id", "id"]),
    ("ix_notifications_user_unread_created", "notifications", ["user_id", "is_read", "created_at"]),
    ("ix_activity_logs_user_created", "activity_logs", ["user_id", "created_at"]),
    ("ix_group_posts_group_status_created", "group_posts", ["group_id", "status", "created_at"]),
    ("ix_conversations_request_inbox", "conversations", ["request_recipient_id", "request_status", "request_updated_at"]),
)


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    for name, table, columns in INDEXES:
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, columns)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    for name, table, _ in reversed(INDEXES):
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name in existing:
            op.drop_index(name, table_name=table)
