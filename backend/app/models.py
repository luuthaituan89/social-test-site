from datetime import datetime, date
from sqlalchemy import (
    String, Text, DateTime, Date, ForeignKey, Enum, UniqueConstraint, Boolean, BigInteger, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
import enum


class Privacy(str, enum.Enum):
    public = "public"
    friends = "friends"
    friends_except = "friends_except"
    specific_friends = "specific_friends"
    followers = "followers"
    custom = "custom"
    only_me = "only_me"


class FriendshipStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    hometown: Mapped[str | None] = mapped_column(String(150), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    relationship_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    relationship_partner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    relationship_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    username_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active_status_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    privacy_settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deletion_scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auth_version: Mapped[int] = mapped_column(default=1)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recovery_codes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def two_factor_enabled(self) -> bool:
        return bool(self.totp_enabled)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    previous_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    device_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    revoke_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)


class AccountToken(Base):
    __tablename__ = "account_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(30), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    addressee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus), default=FriendshipStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    followed_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedAuthorPreference(Base):
    __tablename__ = "feed_author_preferences"
    __table_args__ = (UniqueConstraint("user_id", "author_id", name="uq_feed_author_preference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedPostFeedback(Base):
    __tablename__ = "feed_post_feedback"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_feed_post_feedback"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    show_fewer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedPostCollection(Base):
    __tablename__ = "saved_post_collections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_saved_collection_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedPost(Base):
    __tablename__ = "saved_posts"
    __table_args__ = (UniqueConstraint("collection_id", "post_id", name="uq_saved_collection_post"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("saved_post_collections.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    blocker_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    blocked_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), default="image")
    album_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    privacy: Mapped[Privacy] = mapped_column(Enum(Privacy), default=Privacy.public)
    audience_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    shared_post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_like"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    reaction: Mapped[str] = mapped_column(String(20), default="like")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="likes")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    direct_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pinned_a: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned_b: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_a: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_b: Mapped[bool] = mapped_column(Boolean, default=False)
    cleared_at_a: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cleared_at_b: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    theme: Mapped[str] = mapped_column(String(40), default="default")
    quick_reaction: Mapped[str] = mapped_column(String(20), default="👍")
    nickname_a: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nickname_b: Mapped[str | None] = mapped_column(String(120), nullable=True)
    word_effects: Mapped[str | None] = mapped_column(Text, nullable=True)
    disappearing_seconds: Mapped[int] = mapped_column(default=0)
    muted_until_a: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    muted_until_b: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    restricted_a: Mapped[bool] = mapped_column(Boolean, default=False)
    restricted_b: Mapped[bool] = mapped_column(Boolean, default=False)
    request_recipient_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    request_status: Mapped[str] = mapped_column(String(20), default="accepted", index=True)
    request_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ChatGroup(Base):
    __tablename__ = "chat_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    require_admin_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(40), default="default")
    quick_reaction: Mapped[str] = mapped_column(String(20), default="👍")
    invite_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    invite_token: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    member_customization: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatGroupMember(Base):
    __tablename__ = "chat_group_members"
    __table_args__ = (UniqueConstraint("chat_group_id", "user_id", name="uq_chat_group_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_group_id: Mapped[int] = mapped_column(ForeignKey("chat_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notification_sound: Mapped[str] = mapped_column(String(40), default="default")
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatGroupJoinRequest(Base):
    __tablename__ = "chat_group_join_requests"
    __table_args__ = (UniqueConstraint("chat_group_id", "user_id", name="uq_chat_group_join_request"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_group_id: Mapped[int] = mapped_column(ForeignKey("chat_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatPoll(Base):
    __tablename__ = "chat_polls"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_group_id: Mapped[int] = mapped_column(ForeignKey("chat_groups.id", ondelete="CASCADE"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatPollOption(Base):
    __tablename__ = "chat_poll_options"
    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("chat_polls.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(300))


class ChatPollVote(Base):
    __tablename__ = "chat_poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="uq_chat_poll_vote"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("chat_polls.id", ondelete="CASCADE"), index=True)
    option_id: Mapped[int] = mapped_column(ForeignKey("chat_poll_options.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, default="")
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_mime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_to_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    forwarded_from_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unsent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    view_once: Mapped[bool] = mapped_column(Boolean, default=False)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MessageReaction(Base):
    __tablename__ = "message_reactions"
    __table_args__ = (UniqueConstraint("user_id", "message_id", name="uq_message_reaction"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    reaction: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    message: Mapped[str] = mapped_column(String(500))
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class RelationshipRequest(Base):
    __tablename__ = "relationship_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    addressee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    relationship_status: Mapped[str] = mapped_column(String(50))
    relationship_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Album(Base):
    __tablename__ = "albums"
    __table_args__ = (UniqueConstraint("owner_id", "kind", name="uq_system_album_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    privacy: Mapped[Privacy] = mapped_column(Enum(Privacy), default=Privacy.friends)
    audience_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlbumMedia(Base):
    __tablename__ = "album_media"
    __table_args__ = (UniqueConstraint("album_id", "media_url", name="uq_album_media_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id", ondelete="CASCADE"), index=True)
    media_url: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(20), default="image")
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    privacy: Mapped[Privacy] = mapped_column(Enum(Privacy), default=Privacy.friends)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    description: Mapped[str] = mapped_column(String(500))
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    privacy: Mapped[str] = mapped_column(String(20), default="public", index=True)
    visibility: Mapped[str] = mapped_column(String(20), default="visible", index=True)
    group_type: Mapped[str] = mapped_column(String(30), default="general")
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approval_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    allow_anonymous_posts: Mapped[bool] = mapped_column(Boolean, default=True)
    require_post_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    posting_muted_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupJoinRequest(Base):
    __tablename__ = "group_join_requests"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_join_request"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    answers: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GroupBan(Base):
    __tablename__ = "group_bans"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_ban"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    banned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupPost(Base):
    __tablename__ = "group_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), default="image")
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class GroupPostReaction(Base):
    __tablename__ = "group_post_reactions"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_group_post_reaction"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("group_posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reaction: Mapped[str] = mapped_column(String(20), default="like")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupPostComment(Base):
    __tablename__ = "group_post_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("group_posts.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class GroupPostHidden(Base):
    __tablename__ = "group_post_hidden"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_group_post_hidden"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("group_posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupReport(Base):
    __tablename__ = "group_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("group_posts.id", ondelete="CASCADE"), nullable=True, index=True)
    comment_id: Mapped[int | None] = mapped_column(ForeignKey("group_post_comments.id", ondelete="CASCADE"), nullable=True)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MessageReceipt(Base):
    __tablename__ = "message_receipts"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_message_receipt"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ConversationDraft(Base):
    __tablename__ = "conversation_drafts"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_conversation_draft"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Story(Base):
    __tablename__ = "stories"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(String(1000), default="")
    media_url: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(20), default="image")
    privacy: Mapped[Privacy] = mapped_column(Enum(Privacy), default=Privacy.friends)
    audience_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class StoryView(Base):
    __tablename__ = "story_views"
    __table_args__ = (UniqueConstraint("story_id", "viewer_id", name="uq_story_view"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), index=True)
    viewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Reel(Base):
    __tablename__ = "reels"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    caption: Mapped[str] = mapped_column(String(2200), default="")
    video_url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    privacy: Mapped[Privacy] = mapped_column(Enum(Privacy), default=Privacy.public)
    audience_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    views_count: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SocialPage(Base):
    __tablename__ = "social_pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(80), default="community", index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PageFollower(Base):
    __tablename__ = "page_followers"
    __table_args__ = (UniqueConstraint("page_id", "user_id", name="uq_page_follower"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("social_pages.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    followed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SocialEvent(Base):
    __tablename__ = "social_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    page_id: Mapped[int | None] = mapped_column(ForeignKey("social_pages.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    privacy: Mapped[str] = mapped_column(String(20), default="public", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class EventResponse(Base):
    __tablename__ = "event_responses"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_response"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("social_events.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    response: Mapped[str] = mapped_column(String(20), default="interested", index=True)
    responded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_minor: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    condition: Mapped[str] = mapped_column(String(30), default="used")
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_notification_preference"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    web_push: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
