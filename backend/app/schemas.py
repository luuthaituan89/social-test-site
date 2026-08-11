from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    name: str
    dob: Optional[date] = None
    hometown: Optional[str] = None
    gender: Optional[str] = None
    relationship_status: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None


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


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    dob: Optional[date] = None
    hometown: Optional[str] = Field(default=None, max_length=150)
    gender: Optional[str] = Field(default=None, max_length=30)
    relationship_status: Optional[str] = Field(default=None, max_length=50)
    bio: Optional[str] = None

    @field_validator("dob", mode="before")
    @classmethod
    def empty_date_is_none(cls, value):
        return None if value == "" else value


class PostCreate(BaseModel):
    content: str = ""
    privacy: str = "public"
    image_url: Optional[str] = None
    media_type: Optional[str] = None
    sticker: Optional[str] = Field(default=None, max_length=4000)


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


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UsernameChange(BaseModel):
    username: str = Field(min_length=3, max_length=80)


class ReactionIn(BaseModel):
    reaction: str = "like"


class AlbumCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    privacy: str = "friends"
