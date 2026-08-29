"""Add discovery products, message requests and push preferences.

Revision ID: 0006_engagement_platform
Revises: 0005_smart_feed
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_engagement_platform"
down_revision = "0005_smart_feed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = inspect(op.get_bind())
    conversation_columns = {column["name"] for column in schema.get_columns("conversations")}
    if "request_status" in conversation_columns and schema.has_table("stories") and schema.has_table("push_subscriptions"):
        return
    op.add_column("conversations", sa.Column("request_recipient_id", sa.Integer(), nullable=True))
    op.add_column("conversations", sa.Column("request_status", sa.String(20), nullable=False, server_default="accepted"))
    op.add_column("conversations", sa.Column("request_updated_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_conversation_request_recipient", "conversations", "users", ["request_recipient_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_conversations_request_recipient_id", "conversations", ["request_recipient_id"])
    op.create_index("ix_conversations_request_status", "conversations", ["request_status"])

    for name, column in (
        ("delivered_at", sa.DateTime()), ("read_at", sa.DateTime()),
        ("edited_at", sa.DateTime()), ("viewed_at", sa.DateTime()),
    ):
        op.add_column("messages", sa.Column(name, column, nullable=True))
    op.add_column("messages", sa.Column("view_once", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table("message_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True), sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("message_id", "user_id", name="uq_message_receipt"))
    op.create_index("ix_message_receipts_message_id", "message_receipts", ["message_id"])
    op.create_index("ix_message_receipts_user_id", "message_receipts", ["user_id"])
    op.create_table("conversation_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("conversation_id", "user_id", name="uq_conversation_draft"))
    op.create_index("ix_conversation_drafts_conversation_id", "conversation_drafts", ["conversation_id"])
    op.create_index("ix_conversation_drafts_user_id", "conversation_drafts", ["user_id"])
    op.create_index("ix_conversation_drafts_updated_at", "conversation_drafts", ["updated_at"])

    op.create_table("stories",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.String(1000), nullable=False, server_default=""), sa.Column("media_url", sa.String(500), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=False, server_default="image"),
        sa.Column("privacy", sa.Enum("public", "friends", "friends_except", "specific_friends", "followers", "custom", "only_me", name="privacy"), nullable=False),
        sa.Column("audience_config", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_stories_author_id", "stories", ["author_id"]); op.create_index("ix_stories_created_at", "stories", ["created_at"]); op.create_index("ix_stories_expires_at", "stories", ["expires_at"])
    op.create_table("story_views",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("story_id", sa.Integer(), sa.ForeignKey("stories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("viewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("viewed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("story_id", "viewer_id", name="uq_story_view"))
    op.create_index("ix_story_views_story_id", "story_views", ["story_id"]); op.create_index("ix_story_views_viewer_id", "story_views", ["viewer_id"])

    op.create_table("reels",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("caption", sa.String(2200), nullable=False, server_default=""), sa.Column("video_url", sa.String(500), nullable=False),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("privacy", sa.Enum("public", "friends", "friends_except", "specific_friends", "followers", "custom", "only_me", name="privacy"), nullable=False),
        sa.Column("audience_config", sa.Text(), nullable=True), sa.Column("views_count", sa.BigInteger(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_reels_author_id", "reels", ["author_id"]); op.create_index("ix_reels_created_at", "reels", ["created_at"])

    op.create_table("social_pages",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False), sa.Column("slug", sa.String(100), nullable=False), sa.Column("category", sa.String(80), nullable=False, server_default="community"),
        sa.Column("description", sa.Text(), nullable=True), sa.Column("avatar_url", sa.String(500), nullable=True), sa.Column("cover_url", sa.String(500), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_social_page_slug"))
    op.create_index("ix_social_pages_owner_id", "social_pages", ["owner_id"]); op.create_index("ix_social_pages_name", "social_pages", ["name"]); op.create_index("ix_social_pages_slug", "social_pages", ["slug"]); op.create_index("ix_social_pages_category", "social_pages", ["category"]); op.create_index("ix_social_pages_created_at", "social_pages", ["created_at"])
    op.create_table("page_followers",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("page_id", sa.Integer(), sa.ForeignKey("social_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("followed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("page_id", "user_id", name="uq_page_follower"))
    op.create_index("ix_page_followers_page_id", "page_followers", ["page_id"]); op.create_index("ix_page_followers_user_id", "page_followers", ["user_id"])

    op.create_table("social_events",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("creator_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=True), sa.Column("page_id", sa.Integer(), sa.ForeignKey("social_pages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("location_name", sa.String(255), nullable=True), sa.Column("latitude", sa.Float(), nullable=True), sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False), sa.Column("ends_at", sa.DateTime(), nullable=True), sa.Column("privacy", sa.String(20), nullable=False, server_default="public"), sa.Column("created_at", sa.DateTime(), nullable=False))
    for name in ("creator_id", "group_id", "page_id", "title", "starts_at", "privacy", "created_at"): op.create_index(f"ix_social_events_{name}", "social_events", [name])
    op.create_table("event_responses",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_id", sa.Integer(), sa.ForeignKey("social_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("response", sa.String(20), nullable=False, server_default="interested"), sa.Column("responded_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_response"))
    op.create_index("ix_event_responses_event_id", "event_responses", ["event_id"]); op.create_index("ix_event_responses_user_id", "event_responses", ["user_id"]); op.create_index("ix_event_responses_response", "event_responses", ["response"])

    op.create_table("marketplace_listings",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("seller_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("price_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="VND"), sa.Column("condition", sa.String(30), nullable=False, server_default="used"),
        sa.Column("location_name", sa.String(255), nullable=True), sa.Column("media_url", sa.String(500), nullable=True), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(), nullable=False))
    for name in ("seller_id", "title", "price_minor", "location_name", "status", "created_at"): op.create_index(f"ix_marketplace_listings_{name}", "marketplace_listings", [name])

    op.create_table("notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False), sa.Column("in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("web_push", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("email", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "category", name="uq_notification_preference"))
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"]); op.create_index("ix_notification_preferences_category", "notification_preferences", ["category"])
    op.create_table("push_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint_hash", sa.String(64), nullable=False), sa.Column("endpoint", sa.Text(), nullable=False), sa.Column("p256dh", sa.String(255), nullable=False), sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("last_used_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("endpoint_hash", name="uq_push_endpoint_hash"))
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"]); op.create_index("ix_push_subscriptions_endpoint_hash", "push_subscriptions", ["endpoint_hash"])


def downgrade() -> None:
    for table in ("push_subscriptions", "notification_preferences", "marketplace_listings", "event_responses", "social_events", "page_followers", "social_pages", "reels", "story_views", "stories", "conversation_drafts", "message_receipts"):
        op.drop_table(table)
    for name in ("view_once", "viewed_at", "edited_at", "read_at", "delivered_at"):
        op.drop_column("messages", name)
    op.drop_constraint("fk_conversation_request_recipient", "conversations", type_="foreignkey")
    for name in ("request_updated_at", "request_status", "request_recipient_id"):
        op.drop_column("conversations", name)
