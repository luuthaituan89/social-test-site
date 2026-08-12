import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import ActivityLog, User

router = APIRouter(prefix="/api/activity", tags=["Activity log"])
ALLOWED_CATEGORIES = {"posts", "friends", "search", "security", "profile"}


@router.get("")
def activity_log(
    category: str = "all",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(ActivityLog).filter(ActivityLog.user_id == user.id)
    if category in ALLOWED_CATEGORIES:
        query = query.filter(ActivityLog.category == category)
    total = query.count()
    rows = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).offset(offset).limit(limit).all()
    target_ids = {row.target_user_id for row in rows if row.target_user_id}
    targets = {u.id: u for u in db.query(User).filter(User.id.in_(target_ids)).all()} if target_ids else {}
    return {
        "items": [{
            "id": row.id,
            "category": row.category,
            "action": row.action,
            "description": row.description,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": json.loads(row.details) if row.details else {},
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "created_at": row.created_at,
            "target_user": ({
                "id": targets[row.target_user_id].id,
                "name": targets[row.target_user_id].name,
                "username": targets[row.target_user_id].username,
                "avatar_url": targets[row.target_user_id].avatar_url,
            } if row.target_user_id in targets else None),
        } for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
