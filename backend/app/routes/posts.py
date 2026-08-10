from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Post, Like, Comment, User, Privacy, Album, AlbumMedia
from ..schemas import PostCreate, CommentCreate, ReactionIn
from ..auth import get_current_user
from ..utils import are_friends, is_blocked_either_way
from ..notifications import create_notification
from .notifications import notification_ws

router = APIRouter(prefix="/api/posts", tags=["Posts"])
REACTIONS = {"like": ("👍", "liked"), "love": ("❤️", "loved"), "haha": ("😂", "reacted to"), "wow": ("😮", "reacted to"), "sad": ("😢", "reacted to"), "angry": ("😡", "reacted to")}


def can_view(post: Post, db: Session, viewer: User) -> bool:
    if post.author_id == viewer.id:
        return True

    if is_blocked_either_way(db, post.author_id, viewer.id):
        return False

    if post.privacy == Privacy.public:
        return True

    if post.privacy == Privacy.friends:
        return are_friends(db, post.author_id, viewer.id)

    return False


def can_interact(post: Post, db: Session, viewer: User) -> bool:
    return can_view(post, db, viewer)


def serialize_comment(comment: Comment):
    return {
        "id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at,
        "author": {
            "id": comment.author.id,
            "username": comment.author.username,
            "name": comment.author.name,
            "avatar_url": comment.author.avatar_url,
        },
    }


def serialize(post: Post, db: Session, viewer: User):
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post.id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )

    reaction_rows = db.query(Like).filter(Like.post_id == post.id).all()
    reaction_counts = {}
    my_reaction = None
    for row in reaction_rows:
        reaction_counts[row.reaction] = reaction_counts.get(row.reaction, 0) + 1
        if row.user_id == viewer.id:
            my_reaction = row.reaction

    shared = None
    if post.shared_post_id:
        source = db.get(Post, post.shared_post_id)
        if source and can_view(source, db, viewer):
            shared = {
                "id": source.id,
                "content": source.content,
                "image_url": source.image_url,
                "sticker": source.sticker,
                "media_type": source.media_type,
                "privacy": source.privacy.value,
                "created_at": source.created_at,
                "author": {
                    "id": source.author.id,
                    "username": source.author.username,
                    "name": source.author.name,
                    "avatar_url": source.author.avatar_url,
                },
            }

    album = db.get(Album, post.album_id) if post.album_id else None
    return {
        "id": post.id,
        "content": post.content,
        "image_url": post.image_url,
        "sticker": post.sticker,
        "media_type": post.media_type,
        "album": ({"id": album.id, "name": album.name} if album else None),
        "privacy": post.privacy.value,
        "shared_post_id": post.shared_post_id,
        "shared_post": shared,
        "created_at": post.created_at,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "name": post.author.name,
            "avatar_url": post.author.avatar_url,
        },
        "is_owner": post.author_id == viewer.id,
        "likes_count": len(reaction_rows),
        "liked": my_reaction is not None,
        "my_reaction": my_reaction,
        "reaction_counts": reaction_counts,
        "comments": [serialize_comment(c) for c in comments],
    }


@router.get("")
def feed(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(Post)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(200)
        .all()
    )

    visible = [row for row in rows if can_view(row, db, user)]
    return [serialize(row, db, user) for row in visible[:100]]


@router.get("/user/{user_id}")
def user_posts(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")

    rows = (
        db.query(Post)
        .filter(Post.author_id == user_id)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(100)
        .all()
    )

    return [serialize(row, db, user) for row in rows if can_view(row, db, user)]


@router.get("/{post_id}")
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post or not can_view(post, db, user):
        raise HTTPException(404, "Post not found")
    return serialize(post, db, user)


@router.post("")
def create_post(
    data: PostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.privacy not in [p.value for p in Privacy]:
        raise HTTPException(400, "Invalid privacy")

    content = data.content.strip()
    if not content and not data.image_url and not data.sticker:
        raise HTTPException(400, "Post cannot be empty")

    post = Post(
        author_id=user.id,
        content=content,
        image_url=data.image_url,
        sticker=data.sticker,
        privacy=Privacy(data.privacy),
    )

    db.add(post)
    db.commit()
    db.refresh(post)
    return serialize(post, db, user)


@router.put("/{post_id}")
def update_post(
    post_id: int,
    data: PostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    if post.author_id != user.id:
        raise HTTPException(403, "You can only edit your own posts")

    if data.privacy not in [p.value for p in Privacy]:
        raise HTTPException(400, "Invalid privacy")

    content = data.content.strip()
    if not content and not data.image_url and not data.sticker:
        raise HTTPException(400, "Post cannot be empty")

    post.content = content
    post.image_url = data.image_url
    post.sticker = data.sticker
    post.privacy = Privacy(data.privacy)

    db.commit()
    db.refresh(post)
    return serialize(post, db, user)


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    if post.author_id != user.id:
        raise HTTPException(403, "You can only delete your own posts")

    if post.image_url:
        system_album_ids = [x.id for x in db.query(Album).filter(Album.owner_id == user.id, Album.kind.isnot(None)).all()]
        if system_album_ids:
            db.query(AlbumMedia).filter(
                AlbumMedia.album_id.in_(system_album_ids), AlbumMedia.media_url == post.image_url
            ).delete(synchronize_session=False)
        if post.album_id:
            db.query(AlbumMedia).filter(AlbumMedia.album_id == post.album_id,
                                        AlbumMedia.media_url == post.image_url).delete(synchronize_session=False)
        text = (post.content or "").lower()
        if "profile picture" in text and user.avatar_url == post.image_url:
            user.avatar_url = None
        if "cover photo" in text and user.cover_url == post.image_url:
            user.cover_url = None
    db.delete(post)
    db.commit()
    return {"message": "Post deleted"}


@router.post("/{post_id}/like")
async def toggle_like(
    post_id: int,
    data: ReactionIn = ReactionIn(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post or not can_interact(post, db, user):
        raise HTTPException(404, "Post not found")
    if data.reaction not in REACTIONS:
        raise HTTPException(400, "Invalid reaction")

    like = (
        db.query(Like)
        .filter(Like.post_id == post_id, Like.user_id == user.id)
        .first()
    )

    if like:
        if like.reaction == data.reaction:
            db.delete(like)
            my_reaction = None
        else:
            like.reaction = data.reaction
            my_reaction = data.reaction
    else:
        db.add(Like(post_id=post_id, user_id=user.id, reaction=data.reaction))
        my_reaction = data.reaction

    if my_reaction:
        emoji, verb = REACTIONS[my_reaction]
        create_notification(
            db,
            user_id=post.author_id,
            actor_id=user.id,
            type="post_reaction",
            message=f"{user.name} {verb} your post {emoji}",
            entity_type="post",
            entity_id=post.id,
        )
    db.commit()
    if my_reaction:
        await notification_ws.send(post.author_id, {"type": "notification_refresh", "reason": "post_reaction"})
    rows = db.query(Like).filter(Like.post_id == post_id).all()
    counts = {}
    for row in rows: counts[row.reaction] = counts.get(row.reaction, 0) + 1
    return {"liked": my_reaction is not None, "my_reaction": my_reaction, "likes_count": len(rows), "reaction_counts": counts}


@router.post("/{post_id}/comments")
def comment(
    post_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post or not can_interact(post, db, user):
        raise HTTPException(404, "Post not found")

    content = data.content.strip()
    if not content:
        raise HTTPException(400, "Comment cannot be empty")

    row = Comment(
        post_id=post_id,
        author_id=user.id,
        content=content,
    )
    db.add(row)
    db.flush()

    create_notification(
        db,
        user_id=post.author_id,
        actor_id=user.id,
        type="post_comment",
        message=f"{user.name} commented on your post",
        entity_type="post",
        entity_id=post.id,
    )

    db.commit()
    db.refresh(row)

    return serialize_comment(row)


@router.delete("/{post_id}/comments/{comment_id}")
def delete_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if not comment or comment.post_id != post_id:
        raise HTTPException(404, "Comment not found")

    post = db.get(Post, post_id)
    if comment.author_id != user.id and post.author_id != user.id:
        raise HTTPException(403, "You cannot delete this comment")

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}


@router.post("/{post_id}/share")
def share(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    source = db.get(Post, post_id)
    if not source or not can_view(source, db, user):
        raise HTTPException(404, "Post not found")

    shared = Post(
        author_id=user.id,
        content="",
        privacy=Privacy.public,
        shared_post_id=source.id,
    )
    db.add(shared)
    db.flush()

    create_notification(
        db,
        user_id=source.author_id,
        actor_id=user.id,
        type="post_share",
        message=f"{user.name} shared your post",
        entity_type="post",
        entity_id=source.id,
    )

    db.commit()
    db.refresh(shared)
    return serialize(shared, db, user)
