from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from ..database import get_db
from ..models import User, Friendship, FriendshipStatus, Block
from ..auth import get_current_user
from ..notifications import create_notification

router = APIRouter(prefix="/api/friends", tags=["Friends"])


def pair_filter(a, b):
    return or_(
        and_(Friendship.requester_id == a, Friendship.addressee_id == b),
        and_(Friendship.requester_id == b, Friendship.addressee_id == a),
    )


@router.get("")
def friends(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Friendship).filter(
        pair_filter(user.id, user.id) if False else
        or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
        Friendship.status == FriendshipStatus.accepted,
    ).all()
    ids = [r.addressee_id if r.requester_id == user.id else r.requester_id for r in rows]
    return db.query(User).filter(User.id.in_(ids)).all() if ids else []


@router.get("/requests")
def requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Friendship).filter(
        Friendship.addressee_id == user.id,
        Friendship.status == FriendshipStatus.pending,
    ).all()
    return [
        {"id": r.id, "user": db.get(User, r.requester_id), "created_at": r.created_at}
        for r in rows
    ]


@router.post("/{target_id}")
def send_request(target_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if target_id == user.id:
        raise HTTPException(400, "Cannot add yourself")
    if not db.get(User, target_id):
        raise HTTPException(404, "User not found")
    if db.query(Block).filter(
        or_(
            and_(Block.blocker_id == user.id, Block.blocked_id == target_id),
            and_(Block.blocker_id == target_id, Block.blocked_id == user.id),
        )
    ).first():
        raise HTTPException(403, "Cannot interact with this user")

    existing = db.query(Friendship).filter(pair_filter(user.id, target_id)).first()
    if existing:
        if existing.status == FriendshipStatus.accepted:
            return {"message": "Already friends"}
        raise HTTPException(409, "Friend request already exists")

    friendship = Friendship(requester_id=user.id, addressee_id=target_id)
    db.add(friendship)
    db.flush()
    create_notification(
        db, user_id=target_id, actor_id=user.id, type="friend_request",
        message=f"{user.name} sent you a friend request",
        entity_type="friendship", entity_id=friendship.id,
    )
    db.commit()
    return {"message": "Friend request sent"}


@router.post("/{request_id}/accept")
def accept_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Friendship, request_id)
    if not row or row.addressee_id != user.id:
        raise HTTPException(404, "Request not found")
    row.status = FriendshipStatus.accepted
    create_notification(
        db, user_id=row.requester_id, actor_id=user.id, type="friend_accept",
        message=f"{user.name} accepted your friend request",
        entity_type="friendship", entity_id=row.id,
    )
    db.commit()
    return {"message": "Friend request accepted"}


@router.post("/{request_id}/reject")
def reject_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Friendship, request_id)
    if not row or row.addressee_id != user.id:
        raise HTTPException(404, "Request not found")
    row.status = FriendshipStatus.rejected
    db.commit()
    return {"message": "Friend request rejected"}


@router.delete("/{target_id}")
def unfriend(target_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Friendship).filter(pair_filter(user.id, target_id)).delete(synchronize_session=False)
    db.commit()
    return {"message": "Friendship removed"}
