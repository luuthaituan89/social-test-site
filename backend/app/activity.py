import json
from sqlalchemy.orm import Session

from .models import ActivityLog


def log_activity(
    db: Session,
    user_id: int,
    category: str,
    action: str,
    description: str,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    target_user_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    row = ActivityLog(
        user_id=user_id,
        category=category,
        action=action,
        description=description[:500],
        entity_type=entity_type,
        entity_id=entity_id,
        target_user_id=target_user_id,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:500] or None,
    )
    db.add(row)
    return row
