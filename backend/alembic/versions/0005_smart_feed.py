"""Add smart feed preferences, feedback and saved collections.

Revision ID: 0005_smart_feed
Revises: 0004_account_security
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_smart_feed"
down_revision = "0004_account_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("feed_author_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("snoozed_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "author_id", name="uq_feed_author_preference"))
    op.create_index("ix_feed_author_preferences_user_id", "feed_author_preferences", ["user_id"])
    op.create_index("ix_feed_author_preferences_author_id", "feed_author_preferences", ["author_id"])
    op.create_index("ix_feed_author_preferences_snoozed_until", "feed_author_preferences", ["snoozed_until"])
    op.create_table("feed_post_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_fewer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "post_id", name="uq_feed_post_feedback"))
    op.create_index("ix_feed_post_feedback_user_id", "feed_post_feedback", ["user_id"])
    op.create_index("ix_feed_post_feedback_post_id", "feed_post_feedback", ["post_id"])
    op.create_table("saved_post_collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_saved_collection_name"))
    op.create_index("ix_saved_post_collections_user_id", "saved_post_collections", ["user_id"])
    op.create_table("saved_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("saved_post_collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("collection_id", "post_id", name="uq_saved_collection_post"))
    op.create_index("ix_saved_posts_collection_id", "saved_posts", ["collection_id"])
    op.create_index("ix_saved_posts_post_id", "saved_posts", ["post_id"])
    op.create_index("ix_saved_posts_saved_at", "saved_posts", ["saved_at"])


def downgrade() -> None:
    op.drop_table("saved_posts")
    op.drop_table("saved_post_collections")
    op.drop_table("feed_post_feedback")
    op.drop_table("feed_author_preferences")
