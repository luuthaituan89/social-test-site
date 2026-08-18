from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional, Literal


AudienceName = Literal["public", "friends", "friends_except", "specific_friends", "followers", "custom", "only_me"]


class AudienceConfig(BaseModel):
    included_ids: list[int] = Field(default_factory=list, max_length=500)
    excluded_ids: list[int] = Field(default_factory=list, max_length=500)
    base: Literal["public", "friends", "followers"] = "friends"


class ProfileFieldPrivacy(AudienceConfig):
    audience: AudienceName = "friends"


class PrivacySettingsUpdate(BaseModel):
    dob: ProfileFieldPrivacy
    hometown: ProfileFieldPrivacy
    relationship: ProfileFieldPrivacy
    albums: ProfileFieldPrivacy
    friends_list: ProfileFieldPrivacy


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    name: str
    dob: Optional[date] = None
    hometown: Optional[str] = None
    gender: Optional[str] = None
    relationship_status: Optional[str] = None
    relationship_partner_id: Optional[int] = None
    relationship_since: Optional[date] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    active_status_enabled: bool = True
    account_status: str = "active"
    email_verified: bool = False
    two_factor_enabled: bool = False


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
    expires_in: int = 900
    verification_required: bool = False


class LoginResult(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserPublic] = None
    expires_in: int = 900
    requires_2fa: bool = False
    challenge_token: Optional[str] = None
    verification_required: bool = False


class TwoFactorLoginIn(BaseModel):
    challenge_token: str
    code: str = Field(min_length=6, max_length=20)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=300)
    new_password: str = Field(min_length=8, max_length=128)


class TokenConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=300)


class PasswordConfirm(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class TwoFactorConfirm(BaseModel):
    code: str = Field(min_length=6, max_length=20)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    dob: Optional[date] = None
    hometown: Optional[str] = Field(default=None, max_length=150)
    gender: Optional[str] = Field(default=None, max_length=30)
    relationship_status: Optional[str] = Field(default=None, max_length=50)
    relationship_partner_id: Optional[int] = None
    relationship_since: Optional[date] = None
    bio: Optional[str] = None

    @field_validator("dob", "relationship_since", mode="before")
    @classmethod
    def empty_date_is_none(cls, value):
        return None if value == "" else value


class PostCreate(BaseModel):
    content: str = ""
    privacy: str = "public"
    image_url: Optional[str] = None
    media_type: Optional[str] = None
    sticker: Optional[str] = Field(default=None, max_length=4000)
    audience: AudienceConfig = Field(default_factory=AudienceConfig)


class PostShareIn(BaseModel):
    destination: str = "feed"
    caption: str = Field(default="", max_length=5000)
    privacy: str = "public"
    target_id: Optional[int] = None
    target_type: Optional[str] = None
    audience: AudienceConfig = Field(default_factory=AudienceConfig)


class FeedAuthorPreferenceIn(BaseModel):
    favorite: Optional[bool] = None
    snooze_days: Optional[int] = Field(default=None, ge=0, le=30)


class SavedCollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SavePostIn(BaseModel):
    collection_id: Optional[int] = None


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class FriendAction(BaseModel):
    user_id: int


class MessageCreate(BaseModel):
    content: str = Field(default="", max_length=5000)
    message_type: str = "text"
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = Field(default=None, max_length=255)
    attachment_mime: Optional[str] = Field(default=None, max_length=120)
    sticker: Optional[str] = Field(default=None, max_length=2000)
    reply_to_id: Optional[int] = None


class ChatGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    member_ids: list[int] = Field(default_factory=list, min_length=1, max_length=100)
    require_admin_approval: bool = False
    first_message: MessageCreate


class ChatGroupUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    require_admin_approval: bool = False
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    theme: str = Field(default="default", max_length=40)
    quick_reaction: str = Field(default="👍", max_length=20)
    invite_enabled: bool = True
    member_customization: bool = False


class DirectChatUpdate(BaseModel):
    theme: str = Field(default="default", max_length=40)
    quick_reaction: str = Field(default="👍", max_length=20)
    my_nickname: Optional[str] = Field(default=None, max_length=120)
    other_nickname: Optional[str] = Field(default=None, max_length=120)
    word_effects: dict[str, str] = Field(default_factory=dict)
    disappearing_seconds: int = Field(default=0, ge=0, le=86400)
    mute_minutes: int = Field(default=0, ge=-1, le=525600)
    restricted: bool = False


class ChatPollCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=10)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UsernameChange(BaseModel):
    username: str = Field(min_length=3, max_length=80)


class ActiveStatusUpdate(BaseModel):
    enabled: bool


class AccountPasswordConfirm(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class DataExportRequest(BaseModel):
    format: Literal["json", "html"] = "json"
    categories: list[Literal["profile", "posts", "comments", "reactions", "messages", "friends", "groups", "activity", "media"]] = Field(default_factory=lambda: ["profile", "posts", "comments", "reactions", "messages", "friends", "groups", "activity", "media"], min_length=1, max_length=9)
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ActivityDeleteRequest(BaseModel):
    category: Literal["search", "login", "posts", "profile", "friends", "security", "all"]
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ReactionIn(BaseModel):
    reaction: str = "like"


class AlbumCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    privacy: str = "friends"
    audience: AudienceConfig = Field(default_factory=AudienceConfig)


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=5000)
    rules: Optional[str] = Field(default=None, max_length=10000)
    privacy: str = "public"
    visibility: str = "visible"
    group_type: str = "general"
    cover_url: Optional[str] = Field(default=None, max_length=500)
    approval_questions: list[str] = Field(default_factory=list, max_length=3)


class GroupJoinIn(BaseModel):
    answers: list[str] = Field(default_factory=list, max_length=3)


class GroupPostCreate(BaseModel):
    content: str = Field(default="", max_length=10000)
    media_url: Optional[str] = Field(default=None, max_length=500)
    media_type: str = "image"
    is_anonymous: bool = False


class GroupUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=5000)
    rules: Optional[str] = Field(default=None, max_length=10000)
    privacy: str = "public"
    visibility: str = "visible"
    cover_url: Optional[str] = Field(default=None, max_length=500)
    approval_questions: list[str] = Field(default_factory=list, max_length=3)
    allow_anonymous_posts: bool = True
    require_post_approval: bool = False


class GroupCoverUpdate(BaseModel):
    cover_url: str = Field(min_length=1, max_length=500)


class GroupCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class GroupReportCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
