from sqlalchemy.orm import Session
from .models import Notification, NotificationPreference
from .tasks import dispatch_notification

def create_notification(db: Session, *, user_id: int, actor_id: int | None, type: str,
                        message: str, entity_type: str | None = None, entity_id: int | None = None):
    if actor_id == user_id:
        return
    if type in {"new_message", "group_mention", "message_request"}: category = "messages"
    elif "friend" in type or "relationship" in type: category = "friend_requests"
    elif "comment" in type: category = "comments"
    elif "reaction" in type or type == "like": category = "reactions"
    elif "group" in type: category = "groups"
    elif "login" in type or "security" in type: category = "security"
    else: category = "other"
    preference = db.query(NotificationPreference).filter_by(user_id=user_id, category=category).first()
    if preference and not preference.in_app and not preference.web_push and not preference.email:
        return
    if not preference or preference.in_app:
        db.add(Notification(user_id=user_id, actor_id=actor_id, type=type, message=message,
                            entity_type=entity_type, entity_id=entity_id))
    try:
        dispatch_notification.delay(user_id, {
            "type": type,
            "message": message,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "category": category,
        })
    except Exception:
        # Persisting the notification must not depend on worker availability.
        pass
