from __future__ import annotations

from datetime import datetime, time, timedelta
from html import escape
from io import BytesIO
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from ..activity import log_activity
from ..auth import get_current_user, verify_password
from ..config import settings
from ..database import get_db
from ..models import (
    ActivityLog, Album, AlbumMedia, ChatGroup, ChatGroupMember, Comment,
    Conversation, Follow, Friendship, Group, GroupMember, GroupPost,
    GroupPostComment, GroupPostReaction, Like, Message, MessageReaction, Post,
    User,
)
from ..schemas import AccountPasswordConfirm, ActivityDeleteRequest, DataExportRequest

router = APIRouter(prefix="/api/account", tags=["Account data lifecycle"])


def _bounds(data) -> tuple[datetime | None, datetime | None]:
    if data.date_from and data.date_to and data.date_from > data.date_to:
        raise HTTPException(400, "Start date must not be after end date")
    start = datetime.combine(data.date_from, time.min) if data.date_from else None
    end = datetime.combine(data.date_to + timedelta(days=1), time.min) if data.date_to else None
    return start, end


def _dated(query, model, start, end):
    column = getattr(model, "created_at", None)
    if column is None:
        column = getattr(model, "joined_at", None)
    if column is not None and start:
        query = query.filter(column >= start)
    if column is not None and end:
        query = query.filter(column < end)
    return query


def _value(value):
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (datetime,)):
        return value.isoformat() + "Z"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _rows(rows, *, exclude=()):
    result = []
    for row in rows:
        result.append({column.key: _value(getattr(row, column.key))
                       for column in inspect(row).mapper.column_attrs
                       if column.key not in exclude})
    return result


def _conversation_ids(db: Session, user_id: int) -> set[int]:
    direct = {row.id for row in db.query(Conversation.id).filter(
        or_(Conversation.user_a_id == user_id, Conversation.user_b_id == user_id)).all()}
    group_ids = {row.chat_group_id for row in db.query(ChatGroupMember.chat_group_id).filter(
        ChatGroupMember.user_id == user_id).all()}
    if group_ids:
        direct.update(row.conversation_id for row in db.query(ChatGroup.conversation_id).filter(
            ChatGroup.id.in_(group_ids)).all())
    return direct


def build_export(db: Session, user: User, data: DataExportRequest) -> dict:
    start, end = _bounds(data)
    selected = set(data.categories)
    payload = {
        "export": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "date_from": data.date_from.isoformat() if data.date_from else None,
            "date_to": data.date_to.isoformat() if data.date_to else None,
            "categories": sorted(selected),
        }
    }
    if "profile" in selected:
        payload["profile"] = _rows([user], exclude={"password_hash"})[0]
    if "posts" in selected:
        payload["posts"] = _rows(_dated(db.query(Post).filter(Post.author_id == user.id), Post, start, end).all())
        payload["group_posts"] = _rows(_dated(db.query(GroupPost).filter(GroupPost.author_id == user.id), GroupPost, start, end).all())
    if "comments" in selected:
        payload["comments"] = _rows(_dated(db.query(Comment).filter(Comment.author_id == user.id), Comment, start, end).all())
        payload["group_comments"] = _rows(_dated(db.query(GroupPostComment).filter(GroupPostComment.author_id == user.id), GroupPostComment, start, end).all())
    if "reactions" in selected:
        payload["post_reactions"] = _rows(_dated(db.query(Like).filter(Like.user_id == user.id), Like, start, end).all())
        payload["message_reactions"] = _rows(_dated(db.query(MessageReaction).filter(MessageReaction.user_id == user.id), MessageReaction, start, end).all())
        payload["group_reactions"] = _rows(_dated(db.query(GroupPostReaction).filter(GroupPostReaction.user_id == user.id), GroupPostReaction, start, end).all())
    if "messages" in selected:
        ids = _conversation_ids(db, user.id)
        query = db.query(Message).filter(Message.conversation_id.in_(ids)) if ids else db.query(Message).filter(False)
        payload["messages"] = _rows(_dated(query, Message, start, end).all())
    if "friends" in selected:
        payload["friendships"] = _rows(_dated(db.query(Friendship).filter(or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id)), Friendship, start, end).all())
        payload["follows"] = _rows(_dated(db.query(Follow).filter(or_(Follow.follower_id == user.id, Follow.followed_id == user.id)), Follow, start, end).all())
    if "groups" in selected:
        payload["owned_groups"] = _rows(_dated(db.query(Group).filter(Group.owner_id == user.id), Group, start, end).all())
        payload["group_memberships"] = _rows(_dated(db.query(GroupMember).filter(GroupMember.user_id == user.id), GroupMember, start, end).all())
    if "activity" in selected:
        payload["activity"] = _rows(_dated(db.query(ActivityLog).filter(ActivityLog.user_id == user.id), ActivityLog, start, end).all())
    if "media" in selected:
        album_ids = [row.id for row in db.query(Album.id).filter(Album.owner_id == user.id).all()]
        album_query = db.query(AlbumMedia).filter(AlbumMedia.album_id.in_(album_ids)) if album_ids else db.query(AlbumMedia).filter(False)
        payload["media"] = {
            "profile": [url for url in (user.avatar_url, user.cover_url) if url],
            "albums": _rows(_dated(album_query, AlbumMedia, start, end).all()),
            "post_urls": [row.image_url for row in _dated(db.query(Post).filter(Post.author_id == user.id, Post.image_url.isnot(None)), Post, start, end).all()],
            "message_attachments": [row.attachment_url for row in _dated(db.query(Message).filter(Message.sender_id == user.id, Message.attachment_url.isnot(None)), Message, start, end).all()],
        }
    return payload


@router.get("/lifecycle")
def lifecycle(user: User = Depends(get_current_user)):
    return {
        "status": user.account_status,
        "deactivated_at": user.deactivated_at,
        "deletion_requested_at": user.deletion_requested_at,
        "deletion_scheduled_for": user.deletion_scheduled_for,
        "deletion_grace_days": settings.account_deletion_grace_days,
        "backup_retention_days": settings.backup_retention_days,
        "policy": "Live database records and owned media are purged after the recovery period. Encrypted backups expire on their normal retention schedule and are not used to selectively restore deleted accounts.",
    }


@router.post("/deactivate")
def deactivate(data: AccountPasswordConfirm, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(400, "Password is incorrect")
    user.account_status = "deactivated"
    user.deactivated_at = datetime.utcnow()
    user.active_status_enabled = False
    log_activity(db, user.id, "security", "account_deactivated", "Temporarily deactivated the account")
    db.commit()
    return {"message": "Account deactivated. Sign in again to reactivate it."}


@router.post("/delete")
def schedule_deletion(data: AccountPasswordConfirm, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(400, "Password is incorrect")
    now = datetime.utcnow()
    user.account_status = "pending_deletion"
    user.deletion_requested_at = now
    user.deletion_scheduled_for = now + timedelta(days=settings.account_deletion_grace_days)
    user.active_status_enabled = False
    log_activity(db, user.id, "security", "account_deletion_requested",
                 f"Requested permanent account deletion after {settings.account_deletion_grace_days} days")
    db.commit()
    return {"message": "Account deletion scheduled", "deletion_scheduled_for": user.deletion_scheduled_for,
            "recovery": "Sign in before this date to cancel deletion and recover the account."}


@router.post("/export")
def export_data(data: DataExportRequest, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    payload = build_export(db, user, data)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if data.format == "html":
        body = ("<!doctype html><html><head><meta charset='utf-8'><title>SocialN data export</title>"
                "<style>body{font-family:system-ui;max-width:1100px;margin:40px auto;padding:0 20px}pre{white-space:pre-wrap;word-break:break-word;background:#f3f4f6;padding:20px}</style>"
                f"</head><body><h1>SocialN data export</h1><p>Account: @{escape(user.username)}</p><pre>{escape(serialized)}</pre></body></html>")
        raw, media_type, extension = body.encode("utf-8"), "text/html; charset=utf-8", "html"
    else:
        raw, media_type, extension = serialized.encode("utf-8"), "application/json", "json"
    log_activity(db, user.id, "security", "data_exported", f"Downloaded a {data.format.upper()} data export", details={"categories": data.categories, "date_from": str(data.date_from or ""), "date_to": str(data.date_to or "")})
    db.commit()
    filename = f"socialn-{user.username}-{datetime.utcnow().date().isoformat()}.{extension}"
    return StreamingResponse(BytesIO(raw), media_type=media_type,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.delete("/activity")
def clear_activity(data: ActivityDeleteRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    start, end = _bounds(data)
    query = db.query(ActivityLog).filter(ActivityLog.user_id == user.id)
    if data.category == "login":
        query = query.filter(ActivityLog.category == "security", ActivityLog.action == "login")
    elif data.category != "all":
        query = query.filter(ActivityLog.category == data.category)
    if start:
        query = query.filter(ActivityLog.created_at >= start)
    if end:
        query = query.filter(ActivityLog.created_at < end)
    deleted = query.delete(synchronize_session=False)
    log_activity(db, user.id, "security", "activity_history_cleared",
                 f"Cleared {deleted} {data.category} activity records",
                 details={"category": data.category, "deleted_count": deleted})
    db.commit()
    return {"message": "Activity history cleared", "deleted_count": deleted}
