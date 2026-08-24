from datetime import datetime, timedelta
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import (
    EventResponse, Group, GroupMember, MarketplaceListing, PageFollower, Privacy,
    Reel, SocialEvent, SocialPage, Story, StoryView, User,
)
from ..schemas import EventCreate, EventResponseIn, MarketplaceCreate, PageCreate, ReelCreate, StoryCreate
from ..services.privacy import can_view_audience, encode_audience_config
from ..utils import friend_ids, has_restricted, is_blocked_either_way

router = APIRouter(prefix="/api", tags=["Discovery products"])


def _audience_config(db: Session, user: User, privacy: str, audience) -> str | None:
    config = audience.model_dump()
    selected = set(config["included_ids"]) | set(config["excluded_ids"])
    if user.id in selected or selected - friend_ids(db, user.id):
        raise HTTPException(400, "Story and reel audiences may only contain your friends")
    if privacy == "specific_friends" and not config["included_ids"]:
        raise HTTPException(400, "Choose at least one specific friend")
    return encode_audience_config(config)


def _can_view(db: Session, viewer: User, owner_id: int, privacy, config: str | None) -> bool:
    value = privacy.value if hasattr(privacy, "value") else str(privacy)
    return can_view_audience(
        db, owner_id=owner_id, viewer_id=viewer.id, audience=value, config=config,
        blocked=is_blocked_either_way(db, owner_id, viewer.id),
        restricted=has_restricted(db, owner_id, viewer.id),
    )


def _person(db: Session, user_id: int):
    row = db.get(User, user_id)
    return {"id": row.id, "name": row.name, "username": row.username, "avatar_url": row.avatar_url} if row else None


def _story(db: Session, row: Story, viewer: User):
    return {"id": row.id, "content": row.content, "media_url": row.media_url,
            "media_type": row.media_type, "privacy": row.privacy.value,
            "created_at": row.created_at, "expires_at": row.expires_at,
            "author": _person(db, row.author_id),
            "viewed": db.query(StoryView.id).filter(StoryView.story_id == row.id, StoryView.viewer_id == viewer.id).first() is not None,
            "views_count": db.query(StoryView).filter(StoryView.story_id == row.id).count() if row.author_id == viewer.id else None}


@router.get("/stories")
def stories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    rows = db.query(Story).filter(Story.expires_at > now).order_by(Story.created_at.desc()).limit(250).all()
    return [_story(db, row, user) for row in rows if _can_view(db, user, row.author_id, row.privacy, row.audience_config)]


@router.post("/stories", status_code=201)
def create_story(data: StoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = Story(author_id=user.id, content=data.content.strip(), media_url=data.media_url,
                media_type=data.media_type, privacy=Privacy(data.privacy),
                audience_config=_audience_config(db, user, data.privacy, data.audience),
                expires_at=datetime.utcnow() + timedelta(hours=24))
    db.add(row); db.commit(); db.refresh(row)
    return _story(db, row, user)


@router.post("/stories/{story_id}/view")
def view_story(story_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Story, story_id)
    if not row or row.expires_at <= datetime.utcnow() or not _can_view(db, user, row.author_id, row.privacy, row.audience_config):
        raise HTTPException(404, "Story not found")
    if row.author_id != user.id and not db.query(StoryView).filter_by(story_id=row.id, viewer_id=user.id).first():
        db.add(StoryView(story_id=row.id, viewer_id=user.id)); db.commit()
    return {"viewed": True}


@router.delete("/stories/{story_id}", status_code=204)
def delete_story(story_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Story, story_id)
    if not row or row.author_id != user.id: raise HTTPException(404, "Story not found")
    db.delete(row); db.commit()


def _reel(db: Session, row: Reel):
    return {"id": row.id, "caption": row.caption, "video_url": row.video_url,
            "thumbnail_url": row.thumbnail_url, "privacy": row.privacy.value,
            "views_count": row.views_count, "created_at": row.created_at,
            "author": _person(db, row.author_id)}


@router.get("/reels")
def reels(cursor: int | None = None, limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Reel)
    if cursor: query = query.filter(Reel.id < cursor)
    rows = query.order_by(Reel.id.desc()).limit(limit + 1).all()
    visible = [row for row in rows if _can_view(db, user, row.author_id, row.privacy, row.audience_config)][:limit]
    return {"items": [_reel(db, row) for row in visible], "next_cursor": visible[-1].id if len(visible) == limit else None}


@router.post("/reels", status_code=201)
def create_reel(data: ReelCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = Reel(author_id=user.id, caption=data.caption.strip(), video_url=data.video_url,
               thumbnail_url=data.thumbnail_url, privacy=Privacy(data.privacy),
               audience_config=_audience_config(db, user, data.privacy, data.audience))
    db.add(row); db.commit(); db.refresh(row)
    return _reel(db, row)


@router.post("/reels/{reel_id}/view")
def view_reel(reel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Reel, reel_id)
    if not row or not _can_view(db, user, row.author_id, row.privacy, row.audience_config): raise HTTPException(404, "Reel not found")
    row.views_count += 1; db.commit()
    return {"views_count": row.views_count}


def _page(db: Session, row: SocialPage, viewer_id: int):
    return {"id": row.id, "name": row.name, "slug": row.slug, "category": row.category,
            "description": row.description, "avatar_url": row.avatar_url, "cover_url": row.cover_url,
            "owner": _person(db, row.owner_id), "followers_count": db.query(PageFollower).filter_by(page_id=row.id).count(),
            "following": db.query(PageFollower.id).filter_by(page_id=row.id, user_id=viewer_id).first() is not None}


@router.get("/pages")
def pages(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(SocialPage)
    if q.strip(): query = query.filter(or_(SocialPage.name.ilike(f"%{q.strip()}%"), SocialPage.category.ilike(f"%{q.strip()}%")))
    return [_page(db, row, user.id) for row in query.order_by(SocialPage.created_at.desc()).limit(50).all()]


@router.post("/pages", status_code=201)
def create_page(data: PageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = SocialPage(owner_id=user.id, **data.model_dump())
    db.add(row)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Page address is already in use")
    db.refresh(row); return _page(db, row, user.id)


@router.post("/pages/{page_id}/follow")
def follow_page(page_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(SocialPage, page_id): raise HTTPException(404, "Page not found")
    row = db.query(PageFollower).filter_by(page_id=page_id, user_id=user.id).first()
    if row: db.delete(row); following = False
    else: db.add(PageFollower(page_id=page_id, user_id=user.id)); following = True
    db.commit(); return {"following": following}


def _event(db: Session, row: SocialEvent, viewer_id: int):
    mine = db.query(EventResponse).filter_by(event_id=row.id, user_id=viewer_id).first()
    return {"id": row.id, "title": row.title, "description": row.description, "cover_url": row.cover_url,
            "location_name": row.location_name, "latitude": row.latitude, "longitude": row.longitude,
            "starts_at": row.starts_at, "ends_at": row.ends_at, "privacy": row.privacy,
            "group_id": row.group_id, "page_id": row.page_id, "creator": _person(db, row.creator_id),
            "my_response": mine.response if mine else None,
            "going_count": db.query(EventResponse).filter_by(event_id=row.id, response="going").count()}


@router.get("/events")
def events(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(SocialEvent).filter(SocialEvent.starts_at >= datetime.utcnow() - timedelta(days=1)).order_by(SocialEvent.starts_at).limit(100).all()
    return [_event(db, row, user.id) for row in rows if row.privacy == "public" or row.creator_id == user.id or (row.group_id and db.query(GroupMember.id).filter_by(group_id=row.group_id, user_id=user.id).first())]


@router.post("/events", status_code=201)
def create_event(data: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.ends_at and data.ends_at <= data.starts_at: raise HTTPException(400, "End time must be after start time")
    if data.group_id and not db.query(GroupMember.id).filter_by(group_id=data.group_id, user_id=user.id).first(): raise HTTPException(403, "Join the group before creating an event")
    if data.page_id:
        page = db.get(SocialPage, data.page_id)
        if not page or page.owner_id != user.id: raise HTTPException(403, "Only the page owner can create this event")
    row = SocialEvent(creator_id=user.id, **data.model_dump())
    db.add(row); db.commit(); db.refresh(row); return _event(db, row, user.id)


@router.put("/events/{event_id}/response")
def respond_event(event_id: int, data: EventResponseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = db.get(SocialEvent, event_id)
    if not event: raise HTTPException(404, "Event not found")
    row = db.query(EventResponse).filter_by(event_id=event_id, user_id=user.id).first()
    if not row: row = EventResponse(event_id=event_id, user_id=user.id); db.add(row)
    row.response = data.response; row.responded_at = datetime.utcnow(); db.commit()
    return {"response": row.response}


def _listing(db: Session, row: MarketplaceListing):
    return {"id": row.id, "title": row.title, "description": row.description,
            "price_minor": row.price_minor, "currency": row.currency, "condition": row.condition,
            "location_name": row.location_name, "media_url": row.media_url, "status": row.status,
            "created_at": row.created_at, "seller": _person(db, row.seller_id)}


@router.get("/marketplace")
def marketplace(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(MarketplaceListing).filter(MarketplaceListing.status == "active")
    if q.strip(): query = query.filter(or_(MarketplaceListing.title.ilike(f"%{q.strip()}%"), MarketplaceListing.description.ilike(f"%{q.strip()}%")))
    rows = query.order_by(MarketplaceListing.created_at.desc()).limit(100).all()
    return [_listing(db, row) for row in rows if not is_blocked_either_way(db, row.seller_id, user.id)]


@router.post("/marketplace", status_code=201)
def create_listing(data: MarketplaceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = data.model_dump(); payload["currency"] = payload["currency"].upper()
    row = MarketplaceListing(seller_id=user.id, **payload)
    db.add(row); db.commit(); db.refresh(row); return _listing(db, row)


@router.patch("/marketplace/{listing_id}/status")
def listing_status(listing_id: int, status: str = Query(pattern="^(active|sold|reserved|archived)$"), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(MarketplaceListing, listing_id)
    if not row or row.seller_id != user.id: raise HTTPException(404, "Listing not found")
    row.status = status; db.commit(); return _listing(db, row)
