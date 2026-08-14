from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pathlib import Path
import uuid
import shutil
import re
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, Block, Friendship, FriendshipStatus, Post, Privacy, RelationshipRequest, Notification
from ..schemas import UserPublic, ProfileUpdate, PasswordChange, UsernameChange
from ..auth import get_current_user, verify_password, hash_password
from ..config import settings
from ..utils import are_friends, is_blocked_either_way, friend_ids
from ..activity import log_activity
from ..notifications import create_notification
from .notifications import notification_ws

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserPublic)
async def update_me(data: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    values = data.model_dump(exclude_unset=True)
    status = values.get("relationship_status", user.relationship_status) or None
    allowed = {None, "single", "in_a_relationship", "engaged", "married", "civil_union", "domestic_partnership", "open_relationship", "complicated", "separated", "divorced", "widowed", "prefer_not_to_say"}
    if status not in allowed:
        raise HTTPException(400, "Invalid relationship status")
    no_current_partner = {None, "single", "separated", "divorced", "widowed", "prefer_not_to_say"}
    if status in no_current_partner:
        old_partner = db.get(User, user.relationship_partner_id) if user.relationship_partner_id else None
        if old_partner and old_partner.relationship_partner_id == user.id:
            old_partner.relationship_partner_id = None
            detached_partner_id = old_partner.id
            log_activity(db, old_partner.id, "profile", "relationship_unlinked", f"Relationship link with {user.name} was removed", target_user_id=user.id)
        values["relationship_partner_id"] = None
        values["relationship_since"] = None
        pending = db.query(RelationshipRequest).filter(RelationshipRequest.requester_id == user.id, RelationshipRequest.status == "pending").all()
        for request in pending:
            request.status = "cancelled";request.responded_at = datetime.utcnow()
            db.query(Notification).filter(Notification.entity_type == "relationship_request", Notification.entity_id == request.id).delete(synchronize_session=False)
    else:
        partner_id = values.get("relationship_partner_id", user.relationship_partner_id)
        if partner_id == user.id:
            raise HTTPException(400, "You cannot tag yourself as your relationship partner")
        if partner_id and not db.get(User, partner_id):
            raise HTTPException(404, "Relationship partner not found")
        if partner_id and not are_friends(db, user.id, partner_id):
            raise HTTPException(400, "You can only tag someone from your friends list")
        proposed_since = values.get("relationship_since", user.relationship_since)
        unchanged = partner_id == user.relationship_partner_id and status == user.relationship_status and proposed_since == user.relationship_since
        if partner_id and not unchanged:
            partner = db.get(User, partner_id)
            prior = db.query(RelationshipRequest).filter(RelationshipRequest.requester_id == user.id, RelationshipRequest.status == "pending").all()
            for request in prior:
                request.status = "cancelled";request.responded_at = datetime.utcnow()
                db.query(Notification).filter(Notification.entity_type == "relationship_request", Notification.entity_id == request.id).delete(synchronize_session=False)
            request = RelationshipRequest(requester_id=user.id, addressee_id=partner.id, relationship_status=status, relationship_since=proposed_since)
            db.add(request);db.flush()
            create_notification(db, user_id=partner.id, actor_id=user.id, type="relationship_request",
                                message=f"{user.name} wants to add you to their relationship status",
                                entity_type="relationship_request", entity_id=request.id)
            values.pop("relationship_status", None);values.pop("relationship_partner_id", None);values.pop("relationship_since", None)
            log_activity(db, user.id, "profile", "relationship_request_sent", f"Sent a relationship request to {partner.name}", entity_type="relationship_request", entity_id=request.id, target_user_id=partner.id)
    values["relationship_status"] = status
    for key, value in values.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    if 'request' in locals():
        await notification_ws.send(request.addressee_id, {"type": "notification_refresh", "reason": "relationship_request"})
    if 'detached_partner_id' in locals():
        await notification_ws.send(detached_partner_id, {"type": "relationship_refresh", "reason": "relationship_unlinked"})
    return user


def save_upload(upload: UploadFile) -> str:
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, "Only image files are allowed")
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = Path(settings.upload_dir) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return f"/uploads/{filename}"


def possessive_pronoun(user: User) -> str:
    gender = (user.gender or "").strip().lower()
    if gender == "male":
        return "his"
    if gender == "female":
        return "her"
    return "their"


@router.post("/me/avatar", response_model=UserPublic)
def avatar(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.avatar_url = save_upload(file)
    post = Post(
        author_id=user.id,
        content=f"{user.name} updated {possessive_pronoun(user)} profile picture.",
        image_url=user.avatar_url,
        privacy=Privacy.friends,
    )
    db.add(post);db.flush()
    log_activity(db, user.id, "profile", "avatar_updated", "Updated profile picture", entity_type="post", entity_id=post.id, details={"image_url": user.avatar_url})
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me/avatar", response_model=UserPublic)
def delete_avatar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.avatar_url = None
    log_activity(db, user.id, "profile", "avatar_removed", "Removed profile picture")
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/cover", response_model=UserPublic)
def cover(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.cover_url = save_upload(file)
    post = Post(
        author_id=user.id,
        content=f"{user.name} updated {possessive_pronoun(user)} cover photo.",
        image_url=user.cover_url,
        privacy=Privacy.friends,
    )
    db.add(post);db.flush()
    log_activity(db, user.id, "profile", "cover_updated", "Updated cover photo", entity_type="post", entity_id=post.id, details={"image_url": user.cover_url})
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me/cover", response_model=UserPublic)
def delete_cover(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.cover_url = None
    log_activity(db, user.id, "profile", "cover_removed", "Removed cover photo")
    db.commit()
    db.refresh(user)
    return user


def detach_relationship(db: Session, person: User):
    partner = db.get(User, person.relationship_partner_id) if person.relationship_partner_id else None
    if partner and partner.relationship_partner_id == person.id:
        partner.relationship_partner_id = None
    person.relationship_partner_id = None
    person.relationship_since = None
    person.relationship_status = None


@router.post("/relationship-requests/{request_id}/accept")
async def accept_relationship_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    request = db.get(RelationshipRequest, request_id)
    if not request or request.addressee_id != user.id or request.status != "pending":
        raise HTTPException(404, "Relationship request not found")
    requester = db.get(User, request.requester_id)
    if not requester:
        raise HTTPException(404, "Requester not found")
    if not are_friends(db, requester.id, user.id):
        request.status = "cancelled";request.responded_at = datetime.utcnow();db.commit()
        raise HTTPException(400, "You must still be friends to confirm this relationship")
    detach_relationship(db, requester);detach_relationship(db, user)
    requester.relationship_status = request.relationship_status
    requester.relationship_partner_id = user.id
    requester.relationship_since = request.relationship_since
    user.relationship_status = request.relationship_status
    user.relationship_partner_id = requester.id
    user.relationship_since = request.relationship_since
    request.status = "accepted";request.responded_at = datetime.utcnow()
    db.query(Notification).filter(Notification.user_id == user.id, Notification.entity_type == "relationship_request", Notification.entity_id == request.id).delete(synchronize_session=False)
    create_notification(db, user_id=requester.id, actor_id=user.id, type="relationship_accepted",
                        message=f"{user.name} accepted your relationship request", entity_type="relationship_request", entity_id=request.id)
    log_activity(db, requester.id, "profile", "relationship_confirmed", f"Relationship with {user.name} was confirmed", target_user_id=user.id)
    log_activity(db, user.id, "profile", "relationship_confirmed", f"Confirmed relationship with {requester.name}", target_user_id=requester.id)
    db.commit()
    await notification_ws.send(requester.id, {"type": "notification_refresh", "reason": "relationship_accepted"})
    return {"message": "Relationship request accepted"}


@router.post("/relationship-requests/{request_id}/decline")
async def decline_relationship_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    request = db.get(RelationshipRequest, request_id)
    if not request or request.addressee_id != user.id or request.status != "pending":
        raise HTTPException(404, "Relationship request not found")
    requester = db.get(User, request.requester_id)
    request.status = "declined";request.responded_at = datetime.utcnow()
    db.query(Notification).filter(Notification.user_id == user.id, Notification.entity_type == "relationship_request", Notification.entity_id == request.id).delete(synchronize_session=False)
    if requester:
        create_notification(db, user_id=requester.id, actor_id=user.id, type="relationship_declined",
                            message=f"{user.name} declined your relationship request", entity_type="relationship_request", entity_id=request.id)
        log_activity(db, requester.id, "profile", "relationship_request_declined", f"{user.name} declined the relationship request", target_user_id=user.id)
    db.commit()
    if requester:
        await notification_ws.send(requester.id, {"type": "notification_refresh", "reason": "relationship_declined"})
    return {"message": "Relationship request declined"}




@router.get("/suggestions/people")
def people_you_may_know(limit: int = 12, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit=max(1,min(limit,30)); mine=friend_ids(db,user.id)
    blocked={x.blocked_id for x in db.query(Block).filter(Block.blocker_id==user.id).all()} | {x.blocker_id for x in db.query(Block).filter(Block.blocked_id==user.id).all()}
    pending_rows=db.query(Friendship).filter(or_(Friendship.requester_id==user.id,Friendship.addressee_id==user.id),Friendship.status==FriendshipStatus.pending).all()
    pending={r.addressee_id if r.requester_id==user.id else r.requester_id for r in pending_rows}
    excluded=mine|blocked|pending|{user.id}
    q=db.query(User)
    if excluded: q=q.filter(~User.id.in_(excluded))
    scored=[]
    for c in q.limit(100).all(): scored.append((len(mine & friend_ids(db,c.id)),c))
    scored.sort(key=lambda x:(-x[0],x[1].name.lower()))
    return [{"id":c.id,"name":c.name,"username":c.username,"avatar_url":c.avatar_url,"hometown":c.hometown,"mutual_friends_count":m} for m,c in scored[:limit]]

@router.get("/{user_id}/profile")
def public_profile(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    target=db.get(User,user_id)
    if not target: raise HTTPException(404,"User not found")
    if user.id!=target.id and is_blocked_either_way(db,user.id,target.id): raise HTTPException(403,"Profile unavailable")
    mine=friend_ids(db,user.id); theirs=friend_ids(db,target.id); mids=list(mine & theirs)
    mutual=db.query(User).filter(User.id.in_(mids)).limit(12).all() if mids else []
    outgoing=db.query(Friendship).filter(Friendship.requester_id==user.id,Friendship.addressee_id==target.id,Friendship.status==FriendshipStatus.pending).first()
    incoming=db.query(Friendship).filter(Friendship.requester_id==target.id,Friendship.addressee_id==user.id,Friendship.status==FriendshipStatus.pending).first()
    rel='self' if target.id==user.id else ('friends' if are_friends(db,user.id,target.id) else 'outgoing_request' if outgoing else 'incoming_request' if incoming else 'none')
    partner=db.get(User,target.relationship_partner_id) if target.relationship_partner_id else None
    pending_relationship=db.query(RelationshipRequest).filter(RelationshipRequest.requester_id==target.id,RelationshipRequest.status=="pending").order_by(RelationshipRequest.created_at.desc()).first() if user.id==target.id else None
    pending_partner=db.get(User,pending_relationship.addressee_id) if pending_relationship else None
    pending_payload={"id":pending_relationship.id,"relationship_status":pending_relationship.relationship_status,"relationship_since":pending_relationship.relationship_since,"partner":{"id":pending_partner.id,"name":pending_partner.name,"username":pending_partner.username,"avatar_url":pending_partner.avatar_url}} if pending_relationship and pending_partner else None
    return {"user":{"id":target.id,"username":target.username,"name":target.name,"dob":target.dob,"hometown":target.hometown,"gender":target.gender,"relationship_status":target.relationship_status,"relationship_partner_id":target.relationship_partner_id,"relationship_since":target.relationship_since,"relationship_partner":{"id":partner.id,"name":partner.name,"username":partner.username,"avatar_url":partner.avatar_url} if partner else None,"bio":target.bio,"avatar_url":target.avatar_url,"cover_url":target.cover_url,"created_at":target.created_at},"pending_relationship":pending_payload,"relationship":rel,"incoming_request_id":incoming.id if incoming else None,"mutual_friends_count":len(mine & theirs),"mutual_friends":[{"id":x.id,"name":x.name,"username":x.username,"avatar_url":x.avatar_url} for x in mutual]}


@router.get("/username/{username}/profile")
def profile_by_username(username: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(404, "User not found")
    return public_profile(target.id, db, user)


@router.get("/search", response_model=list[UserPublic])
def search(q: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = q.strip()
    if not q:
        return []
    blocked_ids = {
        x.blocked_id for x in db.query(Block).filter(Block.blocker_id == user.id).all()
    }
    blocked_by_ids = {
        x.blocker_id for x in db.query(Block).filter(Block.blocked_id == user.id).all()
    }
    hidden = blocked_ids | blocked_by_ids
    query = db.query(User).filter(
        or_(User.username.like(f"%{q}%"), User.name.like(f"%{q}%")),
        User.id != user.id,
    )
    if hidden:
        query = query.filter(~User.id.in_(hidden))
    results = query.limit(30).all()
    log_activity(db, user.id, "search", "user_search", f'Searched for “{q}”', details={"query": q, "result_count": len(results)})
    db.commit()
    return results


@router.get("/me/blocked")
def blocked_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Block).filter(Block.blocker_id == user.id).order_by(Block.created_at.desc()).all()
    result = []
    for row in rows:
        target = db.get(User, row.blocked_id)
        if target:
            result.append({"id": target.id, "name": target.name, "username": target.username,
                           "avatar_url": target.avatar_url, "blocked_at": row.created_at})
    return result


@router.post("/{target_id}/block")
def block_user(target_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if target_id == user.id or not db.get(User, target_id):
        raise HTTPException(404, "User not found")
    exists = db.query(Block).filter(Block.blocker_id == user.id, Block.blocked_id == target_id).first()
    if not exists:
        db.add(Block(blocker_id=user.id, blocked_id=target_id))
        db.query(Friendship).filter(
            or_(
                (Friendship.requester_id == user.id) & (Friendship.addressee_id == target_id),
                (Friendship.requester_id == target_id) & (Friendship.addressee_id == user.id),
            )
        ).delete(synchronize_session=False)
        db.commit()
    return {"message": "User blocked"}


@router.delete("/{target_id}/block")
def unblock_user(target_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Block).filter(Block.blocker_id == user.id, Block.blocked_id == target_id).delete()
    db.commit()
    return {"message": "User unblocked"}


@router.put("/me/password")
def change_password(data: PasswordChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


USERNAME_COOLDOWN = timedelta(days=30)
RESERVED_USERNAMES = {"settings", "friends", "messages", "notifications", "api", "uploads"}


def username_change_status(user: User):
    next_change_at = user.username_changed_at + USERNAME_COOLDOWN if user.username_changed_at else None
    can_change = next_change_at is None or datetime.utcnow() >= next_change_at
    return {
        "username": user.username,
        "can_change": can_change,
        "last_changed_at": user.username_changed_at,
        "next_change_at": None if can_change else next_change_at,
    }


@router.get("/me/username-status")
def get_username_change_status(user: User = Depends(get_current_user)):
    return username_change_status(user)


@router.put("/me/username")
def change_username(data: UsernameChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    status = username_change_status(user)
    if not status["can_change"]:
        raise HTTPException(429, f"Username can be changed again after {status['next_change_at'].isoformat()}")

    username = data.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._]+", username):
        raise HTTPException(400, "Username may only contain letters, numbers, dots and underscores")
    if username in RESERVED_USERNAMES:
        raise HTTPException(400, "This username is reserved")
    if username == user.username.lower():
        raise HTTPException(400, "This is already your username")
    if db.query(User).filter(User.username == username, User.id != user.id).first():
        raise HTTPException(409, "Username is already taken")

    user.username = username
    user.username_changed_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    result = username_change_status(user)
    result["message"] = "Username changed successfully"
    result["user"] = UserPublic.model_validate(user)
    return result
