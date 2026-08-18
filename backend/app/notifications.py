from sqlalchemy.orm import Session
from .models import Notification
from .tasks import dispatch_notification

def create_notification(db: Session, *, user_id: int, actor_id: int | None, type: str,
                        message: str, entity_type: str | None = None, entity_id: int | None = None):
    if actor_id == user_id:
        return
    db.add(Notification(user_id=user_id, actor_id=actor_id, type=type, message=message,
                        entity_type=entity_type, entity_id=entity_id))
    try:
        dispatch_notification.delay(user_id, {
            "type": type,
            "message": message,
            "entity_type": entity_type,
            "entity_id": entity_id,
        })
    except Exception:
        # Persisting the notification must not depend on worker availability.
        pass
