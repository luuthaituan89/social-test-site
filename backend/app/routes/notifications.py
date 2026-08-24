from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from ..config import settings
from ..database import get_db, SessionLocal
from ..models import AuthSession, Notification, NotificationPreference, PushSubscription, User
from ..schemas import NotificationPreferenceIn, PushSubscriptionIn
from ..auth import get_current_user
from ..services.realtime import DistributedSocketManager

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

def serialize(n, db):
    actor = db.get(User, n.actor_id) if n.actor_id else None
    return {
        "id": n.id, "type": n.type, "message": n.message,
        "entity_type": n.entity_type, "entity_id": n.entity_id,
        "is_read": n.is_read, "created_at": n.created_at,
        "actor": ({
            "id": actor.id, "name": actor.name, "username": actor.username,
            "avatar_url": actor.avatar_url
        } if actor else None)
    }

@router.get("")
def list_notifications(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit = max(1, min(limit, 100))
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(limit).all()
    unread = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()
    return {"unread_count": unread, "items": [serialize(x, db) for x in rows]}

@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"unread_count": db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()}

@router.post("/read-all")
def read_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update(
        {Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read"}

@router.post("/{notification_id}/read")
def read_one(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}


@router.get("/preferences/all")
def notification_preferences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    saved = {row.category: row for row in db.query(NotificationPreference).filter_by(user_id=user.id).all()}
    categories = ("messages", "friend_requests", "comments", "reactions", "groups", "security", "other")
    return [{"category": category, "in_app": saved.get(category).in_app if category in saved else True,
             "web_push": saved.get(category).web_push if category in saved else True,
             "email": saved.get(category).email if category in saved else False} for category in categories]


@router.put("/preferences")
def update_notification_preference(data: NotificationPreferenceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(NotificationPreference).filter_by(user_id=user.id, category=data.category).first()
    if not row:
        row = NotificationPreference(user_id=user.id, category=data.category); db.add(row)
    row.in_app, row.web_push, row.email = data.in_app, data.web_push, data.email
    row.updated_at = datetime.utcnow(); db.commit()
    return data.model_dump()


@router.get("/push/public-key")
def push_public_key():
    return {"enabled": bool(settings.web_push_public_key and settings.web_push_private_key),
            "public_key": settings.web_push_public_key or None}


@router.post("/push/subscriptions", status_code=201)
def subscribe_push(data: PushSubscriptionIn, user_agent: str | None = Header(default=None),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not settings.web_push_public_key or not settings.web_push_private_key:
        raise HTTPException(503, "Web Push is not configured")
    digest = hashlib.sha256(data.endpoint.encode()).hexdigest()
    row = db.query(PushSubscription).filter_by(endpoint_hash=digest).first()
    if not row:
        row = PushSubscription(user_id=user.id, endpoint_hash=digest, endpoint=data.endpoint,
                               p256dh=data.p256dh, auth=data.auth); db.add(row)
    row.user_id, row.endpoint, row.p256dh, row.auth = user.id, data.endpoint, data.p256dh, data.auth
    row.user_agent, row.last_used_at = user_agent, datetime.utcnow(); db.commit()
    return {"subscribed": True}


@router.delete("/push/subscriptions", status_code=204)
def unsubscribe_push(endpoint: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    digest = hashlib.sha256(endpoint.encode()).hexdigest()
    row = db.query(PushSubscription).filter_by(user_id=user.id, endpoint_hash=digest).first()
    if row: db.delete(row); db.commit()


def record_last_seen(user_id: int):
    from datetime import datetime
    db=SessionLocal()
    try:
        user=db.get(User,user_id)
        if user: user.last_seen_at=datetime.utcnow(); db.commit()
    finally: db.close()


notification_ws=DistributedSocketManager("notifications", on_user_offline=record_last_seen)

@router.websocket("/ws")
async def notifications_ws(ws: WebSocket):
    token=ws.query_params.get("token")
    db=SessionLocal()
    try:
        from ..auth import authenticated_user_from_token
        authenticated=authenticated_user_from_token(db,token)
        user_id=authenticated[0].id
        session_id=authenticated[1].id
    except Exception: await ws.close(code=1008); return
    finally: db.close()
    await notification_ws.connect(user_id,ws)
    try:
        while True:
            await ws.receive_text()
            check=SessionLocal()
            try: revoked=check.query(AuthSession).filter(AuthSession.id==session_id,AuthSession.revoked_at.is_(None)).first() is None
            finally: check.close()
            if revoked:
                await ws.close(code=1008)
                break
            await notification_ws.touch(user_id)
    except WebSocketDisconnect: pass
    finally: notification_ws.disconnect(user_id,ws)
