from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from ..config import settings
from ..database import get_db, SessionLocal
from ..models import Notification, User
from ..auth import get_current_user

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


class NotificationSocketManager:
    def __init__(self): self.active={}
    async def connect(self,user_id,ws): await ws.accept(); self.active.setdefault(user_id,set()).add(ws)
    def disconnect(self,user_id,ws):
        sockets=self.active.get(user_id,set()); sockets.discard(ws)
        if not sockets:
            self.active.pop(user_id,None)
            from datetime import datetime
            db=SessionLocal()
            try:
                user=db.get(User,user_id)
                if user: user.last_seen_at=datetime.utcnow(); db.commit()
            finally: db.close()
    async def send(self,user_id,payload):
        for ws in list(self.active.get(user_id,set())):
            try: await ws.send_json(payload)
            except Exception: self.disconnect(user_id,ws)
notification_ws=NotificationSocketManager()

@router.websocket("/ws")
async def notifications_ws(ws: WebSocket):
    token=ws.query_params.get("token")
    try: user_id=int(jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])["sub"])
    except Exception: await ws.close(code=1008); return
    await notification_ws.connect(user_id,ws)
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: notification_ws.disconnect(user_id,ws)
