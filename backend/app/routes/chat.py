from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError
from pathlib import Path
import uuid
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from ..database import get_db, SessionLocal
from ..models import User, Conversation, Message, MessageReaction, Block, ChatGroup, ChatGroupMember, ChatGroupJoinRequest, ChatPoll, ChatPollOption, ChatPollVote
from ..auth import get_current_user
from ..config import settings
from ..schemas import MessageCreate, ReactionIn, ChatGroupCreate, ChatGroupUpdate, ChatPollCreate, DirectChatUpdate
from ..notifications import create_notification
from ..utils import are_friends, has_restricted
from .notifications import notification_ws

router = APIRouter(prefix="/api/chat", tags=["Chat"])
REACTIONS = {"like": "👍", "love": "❤️", "haha": "😂", "wow": "😮", "sad": "😢", "angry": "😡"}


class ConnectionManager:
    def __init__(self):
        self.active: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        sockets = self.active.get(user_id)
        if not sockets:
            return
        sockets.discard(ws)
        if not sockets:
            self.active.pop(user_id, None)

    async def send_user(self, user_id: int, payload: dict):
        dead = []
        for ws in list(self.active.get(user_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


manager = ConnectionManager()


def blocked_between(db: Session, a: int, b: int) -> bool:
    return db.query(Block).filter(
        or_(
            and_(Block.blocker_id == a, Block.blocked_id == b),
            and_(Block.blocker_id == b, Block.blocked_id == a),
        )
    ).first() is not None


def get_or_create_conversation(db: Session, a: int, b: int) -> Conversation:
    low, high = sorted((a, b))
    key = f"{low}:{high}"
    conv = db.query(Conversation).filter(Conversation.direct_key == key).first()

    if not conv:
        try:
            with db.begin_nested():
                conv = Conversation(user_a_id=low, user_b_id=high, direct_key=key)
                db.add(conv)
                db.flush()
        except IntegrityError:
            conv = db.query(Conversation).filter(Conversation.direct_key == key).first()
            if not conv:
                raise

    return conv


def message_preview(db: Session, message_id: int | None) -> dict | None:
    if not message_id:
        return None
    original = db.get(Message, message_id)
    if not original:
        return None
    return {
        "id": original.id,
        "sender_id": original.sender_id,
        "content": "" if original.is_unsent else original.content,
        "message_type": original.message_type,
        "attachment_name": original.attachment_name,
        "is_unsent": original.is_unsent,
    }


def serialize_message(msg: Message, other_user_id: int, db: Session | None = None) -> dict:
    result = {
        "type": "message",
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "from_user_id": msg.sender_id,
        "to_user_id": other_user_id if msg.sender_id != other_user_id else None,
        "content": msg.content,
        "message_type": msg.message_type,
        "attachment_url": msg.attachment_url,
        "attachment_name": msg.attachment_name,
        "attachment_mime": msg.attachment_mime,
        "sticker": msg.sticker,
        "reply_to_id": msg.reply_to_id,
        "reply_to": message_preview(db, msg.reply_to_id) if db else None,
        "forwarded_from_id": msg.forwarded_from_id,
        "is_forwarded": bool(msg.forwarded_from_id),
        "is_pinned": msg.is_pinned,
        "is_unsent": msg.is_unsent,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
    if db and msg.message_type == "poll" and msg.attachment_name:
        try:
            poll = db.get(ChatPoll, int(msg.attachment_name))
            if poll:
                options = db.query(ChatPollOption).filter(ChatPollOption.poll_id == poll.id).all()
                votes = db.query(ChatPollVote).filter(ChatPollVote.poll_id == poll.id).all()
                result["poll"] = {"id": poll.id, "question": poll.question,
                    "options": [{"id": option.id, "label": option.label,
                                 "votes": sum(1 for vote in votes if vote.option_id == option.id)} for option in options]}
        except (TypeError, ValueError):
            pass
    return result


def conversation_state(conv: Conversation, user_id: int):
    side_a = conv.user_a_id == user_id
    return {
        "pinned": conv.pinned_a if side_a else conv.pinned_b,
        "archived": conv.archived_a if side_a else conv.archived_b,
        "cleared_at": conv.cleared_at_a if side_a else conv.cleared_at_b,
        "restricted": conv.restricted_a if side_a else conv.restricted_b,
    }


def set_conversation_state(conv: Conversation, user_id: int, field: str, value):
    side = "a" if conv.user_a_id == user_id else "b"
    setattr(conv, f"{field}_{side}", value)


def direct_chat_settings(conv: Conversation, user_id: int, other: User):
    side = "a" if conv.user_a_id == user_id else "b"
    other_side = "b" if side == "a" else "a"
    try: effects = json.loads(conv.word_effects or "{}")
    except (TypeError, ValueError): effects = {}
    return {"conversation_id": conv.id, "theme": conv.theme or "default",
            "quick_reaction": conv.quick_reaction or "👍",
            "my_nickname": getattr(conv, f"nickname_{side}") or "",
            "other_nickname": getattr(conv, f"nickname_{other_side}") or "",
            "word_effects": effects, "disappearing_seconds": conv.disappearing_seconds or 0,
            "muted_until": getattr(conv, f"muted_until_{side}"),
            "restricted": bool(getattr(conv, f"restricted_{side}")),
            "other": {"id": other.id, "name": other.name, "username": other.username,
                      "avatar_url": other.avatar_url}}


def message_reaction_state(db: Session, message_id: int, viewer_id: int):
    rows = db.query(MessageReaction).filter(MessageReaction.message_id == message_id).all()
    counts = {}
    mine = None
    for row in rows:
        counts[row.reaction] = counts.get(row.reaction, 0) + 1
        if row.user_id == viewer_id: mine = row.reaction
    return counts, mine


def chat_group_members(db: Session, group_id: int):
    rows = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group_id).all()
    result = []
    for row in rows:
        member = db.get(User, row.user_id)
        if member:
            result.append({"id": member.id, "name": member.name, "username": member.username,
                           "avatar_url": member.avatar_url, "role": row.role, "nickname": row.nickname})
    return result


def serialize_chat_group(db: Session, group: ChatGroup, membership: ChatGroupMember):
    requests = []
    if membership.role == "admin":
        for request in db.query(ChatGroupJoinRequest).filter(ChatGroupJoinRequest.chat_group_id == group.id, ChatGroupJoinRequest.status == "pending").all():
            candidate = db.get(User, request.user_id)
            if candidate: requests.append({"id": request.id, "user": {"id": candidate.id, "name": candidate.name, "username": candidate.username, "avatar_url": candidate.avatar_url}})
    return {"id": group.id, "name": group.name, "avatar_url": group.avatar_url, "creator_id": group.creator_id,
            "require_admin_approval": group.require_admin_approval, "theme": group.theme,
            "quick_reaction": group.quick_reaction, "invite_enabled": group.invite_enabled,
            "invite_token": group.invite_token if group.invite_enabled else None,
            "member_customization": group.member_customization,
            "members": chat_group_members(db, group.id), "my_role": membership.role,
            "muted_until": membership.muted_until, "notification_sound": membership.notification_sound,
            "join_requests": requests}


def require_chat_group_member(db: Session, group_id: int, user_id: int):
    group = db.get(ChatGroup, group_id)
    membership = db.query(ChatGroupMember).filter(
        ChatGroupMember.chat_group_id == group_id, ChatGroupMember.user_id == user_id
    ).first()
    if not group or not membership:
        raise HTTPException(404, "Group chat not found")
    return group, membership


def conversation_participant_ids(db: Session, conv: Conversation):
    group = db.query(ChatGroup).filter(ChatGroup.conversation_id == conv.id).first()
    if group:
        return [row.user_id for row in db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id).all()]
    return list({conv.user_a_id, conv.user_b_id})


def validate_message(data: MessageCreate):
    content = data.content.strip()
    if data.message_type not in {"text", "image", "video", "file", "voice", "sticker", "gif"}:
        raise HTTPException(400, "Invalid message type")
    if not content and not data.attachment_url and not data.sticker:
        raise HTTPException(400, "Message cannot be empty")
    if data.message_type not in {"text", "sticker"} and not data.attachment_url:
        raise HTTPException(400, "Attachment is required")
    return content


def notification_message_preview(msg: Message) -> str:
    content = (msg.content or "").strip()
    if content:
        return content[:160]
    labels = {
        "image": "Photo", "video": "Video", "voice": "Voice message",
        "gif": "GIF", "sticker": "Sticker", "poll": "Poll",
    }
    if msg.message_type == "file":
        return (msg.attachment_name or "File")[:160]
    return labels.get(msg.message_type, "New message")


def message_notification_payload(msg: Message, sender: User, *, conversation_id: int,
                                 group: ChatGroup | None = None, silent: bool = False) -> dict:
    return {
        "type": "message_notification",
        "reason": "new_group_message" if group else "new_message",
        "message_id": msg.id,
        "conversation_id": conversation_id,
        "group_chat_id": group.id if group else None,
        "is_group": bool(group),
        "conversation_name": group.name if group else sender.name,
        "conversation_avatar_url": group.avatar_url if group else sender.avatar_url,
        "actor": {"id": sender.id, "name": sender.name, "username": sender.username,
                  "avatar_url": sender.avatar_url},
        "message_type": msg.message_type,
        "preview": notification_message_preview(msg),
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "silent": bool(silent),
    }


def direct_recipient_muted(conv: Conversation, user_id: int) -> bool:
    side = "a" if conv.user_a_id == user_id else "b"
    muted_until = getattr(conv, f"muted_until_{side}")
    return bool(muted_until and muted_until > datetime.utcnow())


async def notify_group_message(db: Session, group: ChatGroup, sender: User, msg: Message):
    payload = {**serialize_message(msg, 0, db), "group_chat_id": group.id,
               "reaction_counts": {}, "my_reaction": None}
    memberships = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id).all()
    mention_tokens = {value.lower() for value in re.findall(r"(?<!\w)@([A-Za-z0-9_]+)", msg.content or "")}
    for membership in memberships:
        member_id = membership.user_id
        await manager.send_user(member_id, payload)
        muted = membership.muted_until and membership.muted_until > datetime.utcnow()
        if member_id != sender.id:
            member = db.get(User, member_id)
            mentioned = "all" in mention_tokens or bool(member and member.username.lower() in mention_tokens)
            if not muted:
                create_notification(db, user_id=member_id, actor_id=sender.id,
                                    type="group_mention" if mentioned else "new_message",
                                    message=f"{sender.name} mentioned you in {group.name}" if mentioned else f"{sender.name} sent a message in {group.name}",
                                    entity_type="chat_group", entity_id=group.id)
    return payload


async def push_group_message_notifications(db: Session, group: ChatGroup, sender: User, msg: Message):
    memberships = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id).all()
    for membership in memberships:
        if membership.user_id == sender.id:
            continue
        muted = bool(membership.muted_until and membership.muted_until > datetime.utcnow())
        try:
            await notification_ws.send(membership.user_id, message_notification_payload(
                msg, sender, conversation_id=group.conversation_id, group=group, silent=muted
            ))
        except Exception:
            # The message is committed; a disconnected notification channel
            # must not turn a successful send into an API error.
            pass


@router.post("/group-conversations")
async def create_group_conversation(data: ChatGroupCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    content = validate_message(data.first_message)
    member_ids = list(dict.fromkeys([int(x) for x in data.member_ids if int(x) != user.id]))
    if not member_ids:
        raise HTTPException(400, "Select at least one other member")
    users = db.query(User).filter(User.id.in_(member_ids)).all()
    if len(users) != len(member_ids):
        raise HTTPException(400, "One or more selected users no longer exist")
    conv = Conversation(user_a_id=user.id, user_b_id=user.id)
    db.add(conv); db.flush()
    group = ChatGroup(conversation_id=conv.id, name=data.name.strip(), creator_id=user.id,
                      require_admin_approval=data.require_admin_approval)
    db.add(group); db.flush()
    db.add(ChatGroupMember(chat_group_id=group.id, user_id=user.id, role="admin"))
    for member_id in member_ids:
        db.add(ChatGroupMember(chat_group_id=group.id, user_id=member_id, role="member"))
    first = data.first_message
    msg = Message(conversation_id=conv.id, sender_id=user.id, content=content,
                  message_type=first.message_type, attachment_url=first.attachment_url,
                  attachment_name=first.attachment_name, attachment_mime=first.attachment_mime,
                  sticker=first.sticker, is_read=False)
    db.add(msg); db.flush()
    payload = await notify_group_message(db, group, user, msg)
    db.commit(); db.refresh(group); db.refresh(msg)
    await push_group_message_notifications(db, group, user, msg)
    creator_membership = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.user_id == user.id).first()
    return {"group": {**serialize_chat_group(db, group, creator_membership), "is_group": True}, "message": payload}


@router.get("/group-conversations/{group_id}/messages")
def group_messages(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from datetime import datetime
    group, membership = require_chat_group_member(db, group_id, user.id)
    rows = db.query(Message).filter(Message.conversation_id == group.conversation_id).order_by(Message.created_at, Message.id).limit(500).all()
    membership.last_read_at = datetime.utcnow()
    db.commit()
    result = []
    for msg in rows:
        counts, mine = message_reaction_state(db, msg.id, user.id)
        result.append({**serialize_message(msg, 0, db), "group_chat_id": group.id,
                       "reaction_counts": counts, "my_reaction": mine})
    return {"group": serialize_chat_group(db, group, membership), "messages": result}


@router.post("/group-conversations/{group_id}/messages")
async def send_group_message(group_id: int, data: MessageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, _ = require_chat_group_member(db, group_id, user.id)
    content = validate_message(data)
    reply = db.get(Message, data.reply_to_id) if data.reply_to_id else None
    if reply and reply.conversation_id != group.conversation_id:
        raise HTTPException(400, "Reply target is not in this group chat")
    msg = Message(conversation_id=group.conversation_id, sender_id=user.id, content=content,
                  message_type=data.message_type, attachment_url=data.attachment_url,
                  attachment_name=data.attachment_name, attachment_mime=data.attachment_mime,
                  sticker=data.sticker, reply_to_id=reply.id if reply else None, is_read=False)
    db.add(msg); db.flush()
    payload = await notify_group_message(db, group, user, msg)
    db.commit(); db.refresh(msg)
    await push_group_message_notifications(db, group, user, msg)
    return payload


@router.post("/group-conversations/{group_id}/polls")
async def create_group_poll(group_id: int, data: ChatPollCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, _ = require_chat_group_member(db, group_id, user.id)
    labels = [value.strip() for value in data.options if value.strip()]
    if len(labels) < 2: raise HTTPException(400, "A poll needs at least two options")
    poll = ChatPoll(chat_group_id=group.id, creator_id=user.id, question=data.question.strip())
    db.add(poll); db.flush()
    for label in labels: db.add(ChatPollOption(poll_id=poll.id, label=label))
    db.flush()
    msg = Message(conversation_id=group.conversation_id, sender_id=user.id, content="",
                  message_type="poll", attachment_name=str(poll.id), is_read=False)
    db.add(msg); db.flush()
    payload = await notify_group_message(db, group, user, msg)
    db.commit()
    db.refresh(msg)
    await push_group_message_notifications(db, group, user, msg)
    return payload


@router.post("/polls/{poll_id}/vote/{option_id}")
async def vote_group_poll(poll_id: int, option_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    poll = db.get(ChatPoll, poll_id)
    if not poll: raise HTTPException(404, "Poll not found")
    group, _ = require_chat_group_member(db, poll.chat_group_id, user.id)
    option = db.get(ChatPollOption, option_id)
    if not option or option.poll_id != poll.id: raise HTTPException(404, "Poll option not found")
    vote = db.query(ChatPollVote).filter(ChatPollVote.poll_id == poll.id, ChatPollVote.user_id == user.id).first()
    if vote: vote.option_id = option.id
    else: db.add(ChatPollVote(poll_id=poll.id, option_id=option.id, user_id=user.id))
    db.commit()
    message = db.query(Message).filter(Message.conversation_id == group.conversation_id,
                                       Message.message_type == "poll", Message.attachment_name == str(poll.id)).first()
    payload = serialize_message(message, 0, db) if message else {"poll": {"id": poll.id}}
    for participant_id in conversation_participant_ids(db, db.get(Conversation, group.conversation_id)):
        await manager.send_user(participant_id, {"type": "poll_updated", "message": payload})
    return payload


@router.put("/group-conversations/{group_id}")
def update_group_conversation(group_id: int, data: ChatGroupUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, membership = require_chat_group_member(db, group_id, user.id)
    if membership.role != "admin": raise HTTPException(403, "Admin access required")
    group.name = data.name.strip(); group.require_admin_approval = data.require_admin_approval
    group.avatar_url = data.avatar_url; group.theme = data.theme; group.quick_reaction = data.quick_reaction
    group.invite_enabled = data.invite_enabled; group.member_customization = data.member_customization
    if group.invite_enabled and not group.invite_token: group.invite_token = uuid.uuid4().hex
    db.commit(); db.refresh(group)
    return {"message": "Group chat updated", "group": serialize_chat_group(db, group, membership)}


@router.put("/group-conversations/{group_id}/members/{member_id}/nickname")
def update_group_nickname(group_id: int, member_id: int, nickname: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, membership = require_chat_group_member(db, group_id, user.id)
    if membership.role != "admin" and not group.member_customization:
        raise HTTPException(403, "Only admins can change nicknames")
    target = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.user_id == member_id).first()
    if not target: raise HTTPException(404, "Member not found")
    target.nickname = nickname.strip()[:120] or None; db.commit()
    return {"message": "Nickname updated"}


@router.put("/group-conversations/{group_id}/preferences")
def update_group_preferences(group_id: int, mute_minutes: int = 0, sound: str = "default", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from datetime import datetime, timedelta
    _, membership = require_chat_group_member(db, group_id, user.id)
    if mute_minutes < 0: membership.muted_until = datetime(9999, 12, 31)
    elif mute_minutes == 0: membership.muted_until = None
    else: membership.muted_until = datetime.utcnow() + timedelta(minutes=min(mute_minutes, 525600))
    membership.notification_sound = sound[:40] if sound else "default"; db.commit()
    return {"muted_until": membership.muted_until, "notification_sound": membership.notification_sound}


@router.post("/group-invites/{token}")
def join_group_chat_by_link(token: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(ChatGroup).filter(ChatGroup.invite_token == token, ChatGroup.invite_enabled == True).first()
    if not group: raise HTTPException(404, "Invitation link is invalid or disabled")
    existing = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.user_id == user.id).first()
    if existing: return {"status": "joined", "group_id": group.id}
    if group.require_admin_approval:
        request = db.query(ChatGroupJoinRequest).filter(ChatGroupJoinRequest.chat_group_id == group.id, ChatGroupJoinRequest.user_id == user.id).first()
        if request: request.status = "pending"
        else: db.add(ChatGroupJoinRequest(chat_group_id=group.id, user_id=user.id, status="pending"))
        db.commit(); return {"status": "pending", "group_id": group.id}
    db.add(ChatGroupMember(chat_group_id=group.id, user_id=user.id, role="member")); db.commit()
    return {"status": "joined", "group_id": group.id}


@router.post("/group-conversations/{group_id}/join-requests/{request_id}/{action}")
def review_group_chat_request(group_id: int, request_id: int, action: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, membership = require_chat_group_member(db, group_id, user.id)
    if membership.role != "admin": raise HTTPException(403, "Admin access required")
    if action not in {"approve", "decline"}: raise HTTPException(400, "Invalid action")
    request = db.get(ChatGroupJoinRequest, request_id)
    if not request or request.chat_group_id != group.id or request.status != "pending": raise HTTPException(404, "Request not found")
    request.status = "approved" if action == "approve" else "declined"
    if action == "approve" and not db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.user_id == request.user_id).first():
        db.add(ChatGroupMember(chat_group_id=group.id, user_id=request.user_id, role="member"))
    db.commit(); return {"message": f"Request {action}d"}


@router.post("/group-conversations/{group_id}/members/{member_id}")
def add_group_chat_member(group_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, membership = require_chat_group_member(db, group_id, user.id)
    if membership.role != "admin": raise HTTPException(403, "Admin access required")
    if not db.get(User, member_id): raise HTTPException(404, "User not found")
    if db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.user_id == member_id).first():
        raise HTTPException(409, "User is already a member")
    db.add(ChatGroupMember(chat_group_id=group.id, user_id=member_id, role="member")); db.commit()
    return {"message": "Member added"}


@router.delete("/group-conversations/{group_id}/members/{member_id}")
def remove_group_chat_member(group_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, membership = require_chat_group_member(db, group_id, user.id)
    if membership.role != "admin" and member_id != user.id: raise HTTPException(403, "Admin access required")
    target = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.user_id == member_id).first()
    if not target: raise HTTPException(404, "Member not found")
    admins = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.role == "admin").count()
    if target.role == "admin" and admins == 1: raise HTTPException(400, "Assign another admin before leaving")
    db.delete(target); db.commit()
    return {"message": "Member removed"}


@router.put("/group-conversations/{group_id}/members/{member_id}/role")
def set_group_chat_role(group_id: int, member_id: int, role: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group, membership = require_chat_group_member(db, group_id, user.id)
    if membership.role != "admin": raise HTTPException(403, "Admin access required")
    if role not in {"admin", "member"}: raise HTTPException(400, "Invalid role")
    target = db.query(ChatGroupMember).filter(ChatGroupMember.chat_group_id == group.id, ChatGroupMember.user_id == member_id).first()
    if not target: raise HTTPException(404, "Member not found")
    target.role = role; db.commit()
    return {"message": "Role updated"}


@router.post("/upload")
async def upload_chat_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    del user
    suffix = Path(file.filename or "file").suffix.lower()
    allowed = {
        ".jpg", ".jpeg", ".png", ".webp", ".gif",
        ".mp3", ".wav", ".ogg", ".webm", ".m4a",
        ".mp4", ".mov", ".m4v", ".avi", ".mkv",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".csv", ".zip", ".rar",
    }
    if suffix not in allowed:
        raise HTTPException(400, "This file type is not allowed")
    filename = f"chat_{uuid.uuid4().hex}{suffix}"
    target = Path(settings.upload_dir) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    max_size = 2048 * 1024 * 1024
    total = 0
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_size:
                    raise HTTPException(413, "File must be 2048 MB or smaller")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    mime = file.content_type or "application/octet-stream"
    kind = "image" if mime.startswith("image/") else "video" if mime.startswith("video/") else "voice" if mime.startswith("audio/") else "file"
    return {"url": f"/uploads/{filename}", "name": file.filename or filename, "mime": mime, "message_type": kind}


@router.get("/conversations")
def conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group_conversation_ids = [row[0] for row in db.query(ChatGroup.conversation_id).all()]
    rows = db.query(Conversation).filter(
        or_(
            Conversation.user_a_id == user.id,
            Conversation.user_b_id == user.id,
        ),
        ~Conversation.id.in_(group_conversation_ids) if group_conversation_ids else True,
    ).all()

    result = []
    for conv in rows:
        other_id = conv.user_b_id if conv.user_a_id == user.id else conv.user_a_id
        other = db.get(User, other_id)

        if not other or blocked_between(db, user.id, other_id):
            continue

        state = conversation_state(conv, user.id)
        if state["restricted"]:
            continue
        last_query = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
        )
        if state["cleared_at"]:
            last_query = last_query.filter(Message.created_at > state["cleared_at"])
        last = last_query.order_by(Message.created_at.desc(), Message.id.desc()).first()
        if state["cleared_at"] and not last:
            continue

        unread_query = db.query(Message).filter(Message.conversation_id == conv.id,
                                                Message.sender_id != user.id, Message.is_read == False)
        if state["cleared_at"]: unread_query = unread_query.filter(Message.created_at > state["cleared_at"])
        result.append({
            "id": conv.id,
            "user": {
                "id": other.id,
                "name": other.name,
                "username": other.username,
                "avatar_url": other.avatar_url,
            },
            "last_message": last.content if last else "",
            "last_message_type": last.message_type if last else None,
            "last_at": last.created_at if last else conv.created_at,
            "pinned": state["pinned"],
            "archived": state["archived"],
            "unread_count": unread_query.count(),
        })

    memberships = db.query(ChatGroupMember).filter(ChatGroupMember.user_id == user.id).all()
    for membership in memberships:
        group = db.get(ChatGroup, membership.chat_group_id)
        if not group: continue
        last = db.query(Message).filter(Message.conversation_id == group.conversation_id).order_by(Message.created_at.desc(), Message.id.desc()).first()
        unread_query = db.query(Message).filter(Message.conversation_id == group.conversation_id, Message.sender_id != user.id)
        if membership.last_read_at: unread_query = unread_query.filter(Message.created_at > membership.last_read_at)
        result.append({
            "id": group.conversation_id, "group_chat_id": group.id, "is_group": True,
            "name": group.name, "avatar_url": group.avatar_url,
            "members": chat_group_members(db, group.id), "my_role": membership.role,
            "require_admin_approval": group.require_admin_approval,
            "theme": group.theme, "quick_reaction": group.quick_reaction,
            "invite_enabled": group.invite_enabled, "invite_token": group.invite_token,
            "member_customization": group.member_customization,
            "muted_until": membership.muted_until, "notification_sound": membership.notification_sound,
            "last_message": last.content if last else "", "last_message_type": last.message_type if last else None,
            "last_at": last.created_at if last else group.created_at, "pinned": False, "archived": False,
            "unread_count": unread_query.count(),
        })
    return sorted(result, key=lambda x: (not x["pinned"], -x["last_at"].timestamp()))


@router.get("/unread-count")
def unread_message_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group_conversation_ids = [row[0] for row in db.query(ChatGroup.conversation_id).all()]
    rows = db.query(Conversation).filter(
        or_(Conversation.user_a_id == user.id, Conversation.user_b_id == user.id),
        ~Conversation.id.in_(group_conversation_ids) if group_conversation_ids else True,
    ).all()
    total = 0
    for conv in rows:
        state = conversation_state(conv, user.id)
        if state["restricted"]:
            continue
        query = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.sender_id != user.id,
            Message.is_read == False,
        )
        if state["cleared_at"]:
            query = query.filter(Message.created_at > state["cleared_at"])
        total += query.count()
    memberships = db.query(ChatGroupMember).filter(ChatGroupMember.user_id == user.id).all()
    for membership in memberships:
        group = db.get(ChatGroup, membership.chat_group_id)
        if group:
            query = db.query(Message).filter(Message.conversation_id == group.conversation_id, Message.sender_id != user.id)
            if membership.last_read_at: query = query.filter(Message.created_at > membership.last_read_at)
            total += query.count()
    return {"unread_count": total}


@router.get("/presence/{other_user_id}")
def user_presence(other_user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    other = db.get(User, other_user_id)
    if not other:
        raise HTTPException(404, "User not found")
    # If the viewed person restricted the requester, do not reveal their
    # current or last activity. The restrictor can still see the other side.
    hidden_by_other = other_user_id != user.id and has_restricted(db, other_user_id, user.id)
    low, high = sorted((user.id, other_user_id))
    direct = db.query(Conversation).filter(Conversation.direct_key == f"{low}:{high}").first()
    previously_messaged = bool(direct and db.query(Message.id).filter(Message.conversation_id == direct.id).first())
    allowed_audience = other_user_id == user.id or are_friends(db, user.id, other_user_id) or previously_messaged
    mutually_visible = bool(allowed_audience and user.active_status_enabled and other.active_status_enabled and not hidden_by_other)
    online = mutually_visible and (other_user_id == user.id or bool(
        notification_ws.active.get(other_user_id) or manager.active.get(other_user_id)
    ))
    return {
        "online": online,
        "last_seen_at": other.last_seen_at if mutually_visible else None,
        "active_status_visible": mutually_visible,
    }


@router.post("/messages/{message_id}/reaction")
async def react_to_message(message_id: int, data: ReactionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.reaction not in REACTIONS:
        raise HTTPException(400, "Invalid reaction")
    msg = db.get(Message, message_id)
    conv = db.get(Conversation, msg.conversation_id) if msg else None
    if not msg or not conv or user.id not in conversation_participant_ids(db, conv):
        raise HTTPException(404, "Message not found")
    row = db.query(MessageReaction).filter(MessageReaction.message_id == message_id, MessageReaction.user_id == user.id).first()
    current = None
    if row:
        if row.reaction == data.reaction:
            db.delete(row)
        else:
            row.reaction = data.reaction; current = data.reaction
    else:
        db.add(MessageReaction(message_id=message_id, user_id=user.id, reaction=data.reaction)); current = data.reaction
    participant_ids = conversation_participant_ids(db, conv)
    other_id = next((x for x in participant_ids if x != user.id), user.id)
    recipient_restricted_reactor = msg.sender_id != user.id and has_restricted(db, msg.sender_id, user.id)
    if current and msg.sender_id != user.id and not recipient_restricted_reactor:
        create_notification(db, user_id=msg.sender_id, actor_id=user.id, type="message_reaction",
                            message=f"{user.name} reacted {REACTIONS[current]} to your message",
                            entity_type="message", entity_id=msg.id)
    db.commit()
    counts, mine = message_reaction_state(db, message_id, user.id)
    payload = {"type": "message_reaction", "message_id": message_id, "reaction_counts": counts,
               "reacting_user_id": user.id, "reaction": current}
    for participant_id in participant_ids:
        await manager.send_user(participant_id, payload)
    if current and msg.sender_id != user.id and not recipient_restricted_reactor:
        await notification_ws.send(msg.sender_id, {"type": "notification_refresh", "reason": "message_reaction"})
    return {**payload, "my_reaction": mine}


@router.post("/conversations/{conversation_id}/pin")
def toggle_pin(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.get(Conversation, conversation_id)
    if not conv or user.id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(404, "Conversation not found")
    state = conversation_state(conv, user.id)
    set_conversation_state(conv, user.id, "pinned", not state["pinned"])
    db.commit()
    return {"pinned": not state["pinned"]}


@router.post("/conversations/{conversation_id}/archive")
def toggle_archive(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.get(Conversation, conversation_id)
    if not conv or user.id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(404, "Conversation not found")
    state = conversation_state(conv, user.id)
    set_conversation_state(conv, user.id, "archived", not state["archived"])
    db.commit()
    return {"archived": not state["archived"]}


@router.delete("/conversations/{conversation_id}")
def clear_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from datetime import datetime
    conv = db.get(Conversation, conversation_id)
    if not conv or user.id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(404, "Conversation not found")
    if conv.user_a_id == conv.user_b_id == user.id:
        db.query(Message).filter(Message.conversation_id == conv.id).delete(synchronize_session=False)
        db.delete(conv)
    else:
        set_conversation_state(conv, user.id, "cleared_at", datetime.utcnow())
        db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.sender_id != user.id,
            Message.is_read == False,
        ).update({Message.is_read: True}, synchronize_session=False)
    db.commit()
    return {"message": "Conversation removed"}


@router.get("/restricted")
def restricted_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Conversation).filter(or_(
        and_(Conversation.user_a_id == user.id, Conversation.restricted_a == True),
        and_(Conversation.user_b_id == user.id, Conversation.restricted_b == True),
    )).all()
    result = []
    for conv in rows:
        other_id = conv.user_b_id if conv.user_a_id == user.id else conv.user_a_id
        other = db.get(User, other_id)
        if other:
            result.append({"id": other.id, "name": other.name, "username": other.username,
                           "avatar_url": other.avatar_url,
                           "restricted_at": conv.created_at})
    return result


@router.delete("/restricted/{other_user_id}")
def unrestrict_conversation(other_user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    low, high = sorted((user.id, other_user_id))
    conv = db.query(Conversation).filter(Conversation.user_a_id == low, Conversation.user_b_id == high).first()
    if not conv: raise HTTPException(404, "Conversation not found")
    set_conversation_state(conv, user.id, "restricted", False)
    db.commit()
    return {"message": "Conversation unrestricted"}


@router.get("/{other_user_id}/settings")
def get_direct_settings(other_user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    other = db.get(User, other_user_id)
    if not other: raise HTTPException(404, "User not found")
    conv = get_or_create_conversation(db, user.id, other_user_id)
    db.commit()
    return direct_chat_settings(conv, user.id, other)


@router.put("/{other_user_id}/settings")
def update_direct_settings(other_user_id: int, data: DirectChatUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    other = db.get(User, other_user_id)
    if not other: raise HTTPException(404, "User not found")
    conv = get_or_create_conversation(db, user.id, other_user_id)
    side = "a" if conv.user_a_id == user.id else "b"
    other_side = "b" if side == "a" else "a"
    conv.theme, conv.quick_reaction = data.theme, data.quick_reaction
    setattr(conv, f"nickname_{side}", data.my_nickname.strip() if data.my_nickname else None)
    setattr(conv, f"nickname_{other_side}", data.other_nickname.strip() if data.other_nickname else None)
    conv.word_effects = json.dumps({str(k).strip(): str(v).strip() for k, v in data.word_effects.items() if str(k).strip() and str(v).strip()}, ensure_ascii=False)
    conv.disappearing_seconds = data.disappearing_seconds
    setattr(conv, f"restricted_{side}", data.restricted)
    mute = None if data.mute_minutes == 0 else (datetime.utcnow() + timedelta(days=3650) if data.mute_minutes == -1 else datetime.utcnow() + timedelta(minutes=data.mute_minutes))
    setattr(conv, f"muted_until_{side}", mute)
    db.commit(); db.refresh(conv)
    return direct_chat_settings(conv, user.id, other)


@router.get("/{other_user_id}/messages")
def messages(
    other_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    other = db.get(User, other_user_id)
    if not other:
        raise HTTPException(404, "User not found")

    if blocked_between(db, user.id, other_user_id):
        raise HTTPException(403, "You cannot message this user")

    conv = get_or_create_conversation(db, user.id, other_user_id)
    db.commit()

    db.query(Message).filter(Message.conversation_id == conv.id, Message.expires_at != None, Message.expires_at <= datetime.utcnow()).delete(synchronize_session=False)
    db.commit()
    query = db.query(Message).filter(Message.conversation_id == conv.id)
    state = conversation_state(conv, user.id)
    if state["cleared_at"]:
        query = query.filter(Message.created_at > state["cleared_at"])
    rows = (
        query
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(500)
        .all()
    )

    changed = False
    for msg in rows:
        # Restricted chats may be read privately without producing Seen or
        # starting a disappearing-message timer for the sender.
        if msg.sender_id == other_user_id and not msg.is_read and not state["restricted"]:
            msg.is_read = True
            if conv.disappearing_seconds:
                msg.expires_at = datetime.utcnow() + timedelta(seconds=conv.disappearing_seconds)
            changed = True

    if changed:
        db.commit()

    result = []
    for m in rows:
        reaction_counts, my_reaction = message_reaction_state(db, m.id, user.id)
        result.append({
        "id": m.id,
        "conversation_id": m.conversation_id,
        "sender_id": m.sender_id,
        "from_user_id": m.sender_id,
        "content": m.content,
        "message_type": m.message_type,
        "attachment_url": m.attachment_url,
        "attachment_name": m.attachment_name,
        "attachment_mime": m.attachment_mime,
        "sticker": m.sticker,
        "reply_to_id": m.reply_to_id,
        "reply_to": message_preview(db, m.reply_to_id),
        "forwarded_from_id": m.forwarded_from_id,
        "is_forwarded": bool(m.forwarded_from_id),
        "is_pinned": m.is_pinned,
        "is_unsent": m.is_unsent,
        "reaction_counts": reaction_counts,
        "my_reaction": my_reaction,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return result


@router.post("/{other_user_id}/messages")
async def send_message(
    other_user_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    other = db.get(User, other_user_id)
    if not other:
        raise HTTPException(404, "User not found")

    if blocked_between(db, user.id, other_user_id):
        raise HTTPException(403, "You cannot message this user")

    content = data.content.strip()
    if data.message_type not in {"text", "image", "video", "file", "voice", "sticker", "gif"}:
        raise HTTPException(400, "Invalid message type")
    if not content and not data.attachment_url and not data.sticker:
        raise HTTPException(400, "Message cannot be empty")
    if data.sticker and len(data.sticker) > 2000:
        raise HTTPException(400, "Invalid sticker")
    if data.message_type == "sticker" and (not data.sticker or data.attachment_url):
        raise HTTPException(400, "Invalid sticker")
    if data.message_type not in {"text", "sticker"} and not data.attachment_url:
        raise HTTPException(400, "Attachment is required")
    if data.message_type == "gif":
        hostname = (urlparse(data.attachment_url or "").hostname or "").lower()
        if hostname != "giphy.com" and not hostname.endswith(".giphy.com"):
            raise HTTPException(400, "Invalid GIPHY URL")

    conv = get_or_create_conversation(db, user.id, other_user_id)
    set_conversation_state(conv, user.id, "archived", False)
    if other_user_id != user.id:
        set_conversation_state(conv, other_user_id, "archived", False)

    reply_to = db.get(Message, data.reply_to_id) if data.reply_to_id else None
    if reply_to and reply_to.conversation_id != conv.id:
        raise HTTPException(400, "Reply target is not in this conversation")
    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        content=content,
        message_type=data.message_type,
        attachment_url=data.attachment_url,
        attachment_name=data.attachment_name,
        attachment_mime=data.attachment_mime,
        sticker=data.sticker,
        reply_to_id=reply_to.id if reply_to else None,
        is_read=False,
    )
    db.add(msg)
    db.flush()

    recipient_restricted_sender = conversation_state(conv, other_user_id)["restricted"]
    recipient_muted = direct_recipient_muted(conv, other_user_id)
    if other_user_id != user.id and not recipient_restricted_sender and not recipient_muted:
        create_notification(
            db,
            user_id=other_user_id,
            actor_id=user.id,
            type="new_message",
            message=f"{user.name} sent you a message",
            entity_type="conversation",
            entity_id=conv.id,
        )

    db.commit()
    db.refresh(msg)

    payload = {**serialize_message(msg, other_user_id, db), "reaction_counts": {}, "my_reaction": None}

    await manager.send_user(user.id, payload)
    if other_user_id != user.id:
        await manager.send_user(other_user_id, payload)

    try:
        if other_user_id == user.id or recipient_restricted_sender:
            return payload
        await notification_ws.send(other_user_id, message_notification_payload(
            msg, user, conversation_id=conv.id, silent=recipient_muted
        ))
    except Exception:
        # Message is already committed; notification push must never make
        # a successful message request fail.
        pass

    return payload


def owned_chat_message(db: Session, message_id: int, user_id: int):
    msg = db.get(Message, message_id)
    conv = db.get(Conversation, msg.conversation_id) if msg else None
    if not msg or not conv or user_id not in conversation_participant_ids(db, conv):
        raise HTTPException(404, "Message not found")
    return msg, conv


@router.post("/messages/{message_id}/pin")
async def toggle_message_pin(message_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    msg, conv = owned_chat_message(db, message_id, user.id)
    if msg.is_unsent:
        raise HTTPException(400, "An unsent message cannot be pinned")
    msg.is_pinned = not msg.is_pinned
    db.commit()
    payload = {"type": "message_updated", "message_id": msg.id, "is_pinned": msg.is_pinned}
    for participant_id in conversation_participant_ids(db, conv):
        await manager.send_user(participant_id, payload)
    return payload


@router.delete("/messages/{message_id}")
async def unsend_message(message_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    msg, conv = owned_chat_message(db, message_id, user.id)
    if msg.sender_id != user.id:
        raise HTTPException(403, "You can only unsend your own messages")
    msg.content = ""
    msg.attachment_url = None
    msg.attachment_name = None
    msg.attachment_mime = None
    msg.sticker = None
    msg.is_unsent = True
    msg.is_pinned = False
    db.query(MessageReaction).filter(MessageReaction.message_id == msg.id).delete(synchronize_session=False)
    db.commit()
    payload = {"type": "message_updated", "message_id": msg.id, "is_unsent": True, "is_pinned": False}
    for participant_id in conversation_participant_ids(db, conv):
        await manager.send_user(participant_id, payload)
    return payload


@router.post("/messages/{message_id}/forward/{recipient_id}")
async def forward_message(message_id: int, recipient_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    source, _ = owned_chat_message(db, message_id, user.id)
    recipient = db.get(User, recipient_id)
    if not recipient:
        raise HTTPException(404, "Recipient not found")
    if source.is_unsent:
        raise HTTPException(400, "An unsent message cannot be forwarded")
    if blocked_between(db, user.id, recipient_id):
        raise HTTPException(403, "You cannot message this user")
    conv = get_or_create_conversation(db, user.id, recipient_id)
    recipient_restricted_sender = conversation_state(conv, recipient_id)["restricted"]
    recipient_muted = direct_recipient_muted(conv, recipient_id)
    forwarded = Message(
        conversation_id=conv.id, sender_id=user.id, content=source.content,
        message_type=source.message_type, attachment_url=source.attachment_url,
        attachment_name=source.attachment_name, attachment_mime=source.attachment_mime,
        sticker=source.sticker, forwarded_from_id=source.id, is_read=False,
    )
    db.add(forwarded);db.flush()
    if recipient_id != user.id and not recipient_restricted_sender and not recipient_muted:
        create_notification(db, user_id=recipient_id, actor_id=user.id, type="new_message",
                            message=f"{user.name} forwarded you a message", entity_type="conversation", entity_id=conv.id)
    db.commit();db.refresh(forwarded)
    payload = {**serialize_message(forwarded, recipient_id, db), "reaction_counts": {}, "my_reaction": None}
    await manager.send_user(user.id, payload)
    if recipient_id != user.id:
        await manager.send_user(recipient_id, payload)
        if not recipient_restricted_sender:
            await notification_ws.send(recipient_id, message_notification_payload(
                forwarded, user, conversation_id=conv.id, silent=recipient_muted
            ))
    return payload


@router.websocket("/ws")
async def websocket_chat(ws: WebSocket):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=1008)
        return

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        await ws.close(code=1008)
        return

    db = SessionLocal()
    user = db.get(User, user_id)

    if not user:
        db.close()
        await ws.close(code=1008)
        return

    await manager.connect(user_id, ws)

    try:
        while True:
            # WebSocket is receive-only for app messages.
            # Client sends text "ping" as keepalive.
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
                continue
            try:
                event = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                continue
            if event.get("type") == "typing":
                try:
                    other_user_id = int(event.get("to_user_id"))
                except (TypeError, ValueError):
                    continue
                if other_user_id == user_id or not db.get(User, other_user_id):
                    continue
                if blocked_between(db, user_id, other_user_id):
                    continue
                # Typing indicators from a restricted account are kept inside
                # the restricted inbox and must not surface as an alert.
                if has_restricted(db, other_user_id, user_id):
                    continue
                await manager.send_user(other_user_id, {
                    "type": "typing",
                    "from_user_id": user_id,
                    "to_user_id": other_user_id,
                    "is_typing": bool(event.get("is_typing")),
                })
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, ws)
        db.close()
