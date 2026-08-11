from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from jose import jwt, JWTError
from pathlib import Path
import uuid
import json

from ..database import get_db, SessionLocal
from ..models import User, Conversation, Message, MessageReaction, Block
from ..auth import get_current_user
from ..config import settings
from ..schemas import MessageCreate, ReactionIn
from ..notifications import create_notification
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
    conv = db.query(Conversation).filter(
        Conversation.user_a_id == low,
        Conversation.user_b_id == high,
    ).first()

    if not conv:
        conv = Conversation(user_a_id=low, user_b_id=high)
        db.add(conv)
        db.flush()

    return conv


def serialize_message(msg: Message, other_user_id: int) -> dict:
    return {
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
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def conversation_state(conv: Conversation, user_id: int):
    side_a = conv.user_a_id == user_id
    return {
        "pinned": conv.pinned_a if side_a else conv.pinned_b,
        "archived": conv.archived_a if side_a else conv.archived_b,
        "cleared_at": conv.cleared_at_a if side_a else conv.cleared_at_b,
    }


def set_conversation_state(conv: Conversation, user_id: int, field: str, value):
    side = "a" if conv.user_a_id == user_id else "b"
    setattr(conv, f"{field}_{side}", value)


def message_reaction_state(db: Session, message_id: int, viewer_id: int):
    rows = db.query(MessageReaction).filter(MessageReaction.message_id == message_id).all()
    counts = {}
    mine = None
    for row in rows:
        counts[row.reaction] = counts.get(row.reaction, 0) + 1
        if row.user_id == viewer_id: mine = row.reaction
    return counts, mine


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
    rows = db.query(Conversation).filter(
        or_(
            Conversation.user_a_id == user.id,
            Conversation.user_b_id == user.id,
        )
    ).all()

    result = []
    for conv in rows:
        other_id = conv.user_b_id if conv.user_a_id == user.id else conv.user_a_id
        other = db.get(User, other_id)

        if not other or blocked_between(db, user.id, other_id):
            continue

        state = conversation_state(conv, user.id)
        last_query = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
        )
        if state["cleared_at"]:
            last_query = last_query.filter(Message.created_at > state["cleared_at"])
        last = last_query.order_by(Message.created_at.desc(), Message.id.desc()).first()
        if state["cleared_at"] and not last:
            continue

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
        })

    return sorted(result, key=lambda x: (not x["pinned"], -x["last_at"].timestamp()))


@router.get("/unread-count")
def unread_message_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Conversation).filter(
        or_(Conversation.user_a_id == user.id, Conversation.user_b_id == user.id)
    ).all()
    total = 0
    for conv in rows:
        state = conversation_state(conv, user.id)
        query = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.sender_id != user.id,
            Message.is_read == False,
        )
        if state["cleared_at"]:
            query = query.filter(Message.created_at > state["cleared_at"])
        total += query.count()
    return {"unread_count": total}


@router.get("/presence/{other_user_id}")
def user_presence(other_user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    other = db.get(User, other_user_id)
    if not other:
        raise HTTPException(404, "User not found")
    online = other_user_id == user.id or bool(
        notification_ws.active.get(other_user_id) or manager.active.get(other_user_id)
    )
    return {
        "online": online,
        "last_seen_at": other.last_seen_at,
    }


@router.post("/messages/{message_id}/reaction")
async def react_to_message(message_id: int, data: ReactionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.reaction not in REACTIONS:
        raise HTTPException(400, "Invalid reaction")
    msg = db.get(Message, message_id)
    conv = db.get(Conversation, msg.conversation_id) if msg else None
    if not msg or not conv or user.id not in (conv.user_a_id, conv.user_b_id):
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
    other_id = conv.user_b_id if conv.user_a_id == user.id else conv.user_a_id
    if current and msg.sender_id != user.id:
        create_notification(db, user_id=msg.sender_id, actor_id=user.id, type="message_reaction",
                            message=f"{user.name} reacted {REACTIONS[current]} to your message",
                            entity_type="message", entity_id=msg.id)
    db.commit()
    counts, mine = message_reaction_state(db, message_id, user.id)
    payload = {"type": "message_reaction", "message_id": message_id, "reaction_counts": counts,
               "reacting_user_id": user.id, "reaction": current}
    await manager.send_user(user.id, payload)
    if other_id != user.id:
        await manager.send_user(other_id, payload)
    if current and msg.sender_id != user.id:
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
        if msg.sender_id == other_user_id and not msg.is_read:
            msg.is_read = True
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
    if data.message_type not in {"text", "image", "video", "file", "voice", "sticker"}:
        raise HTTPException(400, "Invalid message type")
    if not content and not data.attachment_url and not data.sticker:
        raise HTTPException(400, "Message cannot be empty")
    if data.sticker and len(data.sticker) > 2000:
        raise HTTPException(400, "Invalid sticker")
    if data.message_type == "sticker" and (not data.sticker or data.attachment_url):
        raise HTTPException(400, "Invalid sticker")
    if data.message_type not in {"text", "sticker"} and not data.attachment_url:
        raise HTTPException(400, "Attachment is required")

    conv = get_or_create_conversation(db, user.id, other_user_id)
    set_conversation_state(conv, user.id, "archived", False)
    if other_user_id != user.id:
        set_conversation_state(conv, other_user_id, "archived", False)

    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        content=content,
        message_type=data.message_type,
        attachment_url=data.attachment_url,
        attachment_name=data.attachment_name,
        attachment_mime=data.attachment_mime,
        sticker=data.sticker,
        is_read=False,
    )
    db.add(msg)
    db.flush()

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

    payload = {
        "type": "message",
        "id": msg.id,
        "conversation_id": conv.id,
        "sender_id": user.id,
        "from_user_id": user.id,
        "to_user_id": other_user_id,
        "content": msg.content,
        "message_type": msg.message_type,
        "attachment_url": msg.attachment_url,
        "attachment_name": msg.attachment_name,
        "attachment_mime": msg.attachment_mime,
        "sticker": msg.sticker,
        "reaction_counts": {},
        "my_reaction": None,
        "created_at": msg.created_at.isoformat(),
    }

    await manager.send_user(user.id, payload)
    await manager.send_user(other_user_id, payload)

    try:
        await notification_ws.send(other_user_id, {
            "type": "notification_refresh",
            "reason": "new_message",
        })
    except Exception:
        # Message is already committed; notification push must never make
        # a successful message request fail.
        pass

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
