from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Group, MarketplaceListing, Post, Reel, SocialEvent, SocialPage, User
from ..services.privacy import can_view_audience
from ..utils import has_restricted, is_blocked_either_way
from .posts import can_view as can_view_post

router = APIRouter(prefix="/api/search", tags=["Search"])
KINDS = {"people", "posts", "groups", "pages", "reels", "events", "marketplace"}


@router.get("")
def global_search(
    q: str = Query(min_length=1, max_length=120),
    types: str = "people,posts,groups,pages,reels,events,marketplace",
    limit: int = Query(8, ge=1, le=25),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    term = q.strip()
    requested = set(types.split(",")) & KINDS
    result = {kind: [] for kind in KINDS if kind in requested}
    pattern = f"%{term}%"

    if "people" in requested:
        rows = db.query(User).filter(User.account_status == "active", or_(User.name.ilike(pattern), User.username.ilike(pattern))).limit(limit * 2).all()
        result["people"] = [{"id": row.id, "name": row.name, "username": row.username, "avatar_url": row.avatar_url}
                            for row in rows if not is_blocked_either_way(db, row.id, user.id)][:limit]
    if "posts" in requested:
        rows = db.query(Post).filter(Post.content.ilike(pattern)).order_by(Post.created_at.desc()).limit(limit * 5).all()
        result["posts"] = [{"id": row.id, "content": row.content[:300], "media_type": row.media_type,
                            "created_at": row.created_at, "author": {"id": row.author.id, "name": row.author.name,
                            "username": row.author.username, "avatar_url": row.author.avatar_url}}
                           for row in rows if can_view_post(row, db, user)][:limit]
    if "groups" in requested:
        rows = db.query(Group).filter(Group.visibility == "visible", or_(Group.name.ilike(pattern), Group.description.ilike(pattern))).limit(limit).all()
        result["groups"] = [{"id": row.id, "name": row.name, "description": row.description,
                             "privacy": row.privacy, "cover_url": row.cover_url} for row in rows]
    if "pages" in requested:
        rows = db.query(SocialPage).filter(or_(SocialPage.name.ilike(pattern), SocialPage.category.ilike(pattern), SocialPage.description.ilike(pattern))).limit(limit).all()
        result["pages"] = [{"id": row.id, "name": row.name, "slug": row.slug, "category": row.category,
                            "avatar_url": row.avatar_url} for row in rows]
    if "reels" in requested:
        rows = db.query(Reel).filter(Reel.caption.ilike(pattern)).order_by(Reel.created_at.desc()).limit(limit * 3).all()
        result["reels"] = [{"id": row.id, "caption": row.caption, "video_url": row.video_url,
                            "thumbnail_url": row.thumbnail_url} for row in rows
                           if can_view_audience(db, owner_id=row.author_id, viewer_id=user.id,
                                                audience=row.privacy.value, config=row.audience_config,
                                                blocked=is_blocked_either_way(db, row.author_id, user.id),
                                                restricted=has_restricted(db, row.author_id, user.id))][:limit]
    if "events" in requested:
        rows = db.query(SocialEvent).filter(SocialEvent.privacy == "public", or_(SocialEvent.title.ilike(pattern), SocialEvent.description.ilike(pattern), SocialEvent.location_name.ilike(pattern))).limit(limit).all()
        result["events"] = [{"id": row.id, "title": row.title, "starts_at": row.starts_at,
                             "location_name": row.location_name, "cover_url": row.cover_url} for row in rows]
    if "marketplace" in requested:
        rows = db.query(MarketplaceListing).filter(MarketplaceListing.status == "active", or_(MarketplaceListing.title.ilike(pattern), MarketplaceListing.description.ilike(pattern))).limit(limit * 2).all()
        result["marketplace"] = [{"id": row.id, "title": row.title, "price_minor": row.price_minor,
                                  "currency": row.currency, "media_url": row.media_url}
                                 for row in rows if not is_blocked_either_way(db, row.seller_id, user.id)][:limit]
    return {"query": term, "results": result}
