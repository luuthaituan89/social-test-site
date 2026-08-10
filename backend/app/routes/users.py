from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pathlib import Path
import uuid
import shutil
import re
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, Block, Friendship, FriendshipStatus, Post, Privacy
from ..schemas import UserPublic, ProfileUpdate, PasswordChange, UsernameChange
from ..auth import get_current_user, verify_password, hash_password
from ..config import settings
from ..utils import are_friends, is_blocked_either_way, friend_ids

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserPublic)
def update_me(data: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
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
    db.add(Post(
        author_id=user.id,
        content=f"{user.name} updated {possessive_pronoun(user)} profile picture.",
        image_url=user.avatar_url,
        privacy=Privacy.friends,
    ))
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me/avatar", response_model=UserPublic)
def delete_avatar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.avatar_url = None
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/cover", response_model=UserPublic)
def cover(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.cover_url = save_upload(file)
    db.add(Post(
        author_id=user.id,
        content=f"{user.name} updated {possessive_pronoun(user)} cover photo.",
        image_url=user.cover_url,
        privacy=Privacy.friends,
    ))
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me/cover", response_model=UserPublic)
def delete_cover(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.cover_url = None
    db.commit()
    db.refresh(user)
    return user




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
    return {"user":{"id":target.id,"username":target.username,"name":target.name,"dob":target.dob,"hometown":target.hometown,"gender":target.gender,"relationship_status":target.relationship_status,"bio":target.bio,"avatar_url":target.avatar_url,"cover_url":target.cover_url,"created_at":target.created_at},"relationship":rel,"incoming_request_id":incoming.id if incoming else None,"mutual_friends_count":len(mine & theirs),"mutual_friends":[{"id":x.id,"name":x.name,"username":x.username,"avatar_url":x.avatar_url} for x in mutual]}


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
    return query.limit(30).all()


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
