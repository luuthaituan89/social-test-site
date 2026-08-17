from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from .models import Friendship, FriendshipStatus, Block, Conversation


def are_friends(db: Session, a: int, b: int) -> bool:
    row = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == a, Friendship.addressee_id == b),
            and_(Friendship.requester_id == b, Friendship.addressee_id == a),
        ),
        Friendship.status == FriendshipStatus.accepted,
    ).first()
    return row is not None


def is_blocked_either_way(db: Session, a: int, b: int) -> bool:
    return db.query(Block).filter(
        or_(
            and_(Block.blocker_id == a, Block.blocked_id == b),
            and_(Block.blocker_id == b, Block.blocked_id == a),
        )
    ).first() is not None


def has_restricted(db: Session, restrictor_id: int, restricted_id: int) -> bool:
    """Return whether restrictor_id has restricted restricted_id in direct chat."""
    low, high = sorted((restrictor_id, restricted_id))
    conv = db.query(Conversation).filter(
        Conversation.user_a_id == low,
        Conversation.user_b_id == high,
        Conversation.direct_key == f"{low}:{high}",
    ).first()
    if not conv:
        return False
    return bool(conv.restricted_a if conv.user_a_id == restrictor_id else conv.restricted_b)


def friend_ids(db: Session, user_id: int) -> set[int]:
    rows = db.query(Friendship).filter(
        or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
        Friendship.status == FriendshipStatus.accepted,
    ).all()
    return {r.addressee_id if r.requester_id == user_id else r.requester_id for r in rows}
