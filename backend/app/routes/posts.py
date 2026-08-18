from fastapi import APIRouter, Depends, HTTPException
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Post, Like, Comment, User, Privacy, Album, AlbumMedia,
                      Group, GroupMember, GroupPost, ChatGroup,
                      ChatGroupMember, Message)
from ..schemas import PostCreate, PostShareIn, CommentCreate, ReactionIn
from ..auth import get_current_user
from ..utils import are_friends, is_blocked_either_way, has_restricted, friend_ids
from ..notifications import create_notification
from .notifications import notification_ws
from ..activity import log_activity
from ..services.privacy import can_view_audience, decode_config, encode_audience_config

router = APIRouter(prefix="/api/posts", tags=["Posts"])
REACTIONS = {"like": ("👍", "liked"), "love": ("❤️", "loved"), "haha": ("😂", "reacted to"), "wow": ("😮", "reacted to"), "sad": ("😢", "reacted to"), "angry": ("😡", "reacted to")}


def can_view(post: Post, db: Session, viewer: User) -> bool:
    if not post.author or post.author.account_status != "active":
        return False
    if post.media_type == "unavailable":
        return False
    return can_view_audience(
        db, viewer_id=viewer.id, owner_id=post.author_id,
        audience=post.privacy.value, config=post.audience_config,
        blocked=is_blocked_either_way(db, post.author_id, viewer.id),
        restricted=has_restricted(db, post.author_id, viewer.id),
    )


def validated_audience(db: Session, user: User, privacy: str, audience) -> str | None:
    if privacy not in [item.value for item in Privacy]:
        raise HTTPException(400, "Invalid privacy")
    config = audience.model_dump() if hasattr(audience, "model_dump") else (audience or {})
    selected = set(config.get("included_ids", [])) | set(config.get("excluded_ids", []))
    if user.id in selected:
        raise HTTPException(400, "You cannot add yourself to an audience list")
    if selected - friend_ids(db, user.id):
        raise HTTPException(400, "Custom audiences can only contain your friends")
    if privacy == "specific_friends" and not config.get("included_ids"):
        raise HTTPException(400, "Choose at least one specific friend")
    return encode_audience_config(config)


def shared_source_payload(post_id: int, db: Session, viewer: User):
    source = db.get(Post, post_id)
    if not source or not can_view(source, db, viewer):
        return {"id": post_id, "available": False}
    return {
        "id": source.id,
        "available": True,
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


def public_share_count(post_id: int, db: Session) -> int:
    feed_count = db.query(Post).filter(
        Post.shared_post_id == post_id,
        Post.privacy == Privacy.public,
        Post.media_type != "unavailable",
    ).count()
    group_count = db.query(GroupPost).join(Group, Group.id == GroupPost.group_id).filter(
        GroupPost.media_type == "shared_post",
        GroupPost.media_url == str(post_id),
        GroupPost.status == "published",
        Group.privacy == "public",
    ).count()
    return feed_count + group_count


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

    shared = shared_source_payload(post.shared_post_id, db, viewer) if post.shared_post_id else None

    album = db.get(Album, post.album_id) if post.album_id else None
    return {
        "id": post.id,
        "content": post.content,
        "image_url": post.image_url,
        "sticker": post.sticker,
        "media_type": post.media_type,
        "album": ({"id": album.id, "name": album.name} if album else None),
        "privacy": post.privacy.value,
        "audience": decode_config(post.audience_config) if post.author_id == viewer.id else None,
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
        "shares_count": public_share_count(post.shared_post_id or post.id, db),
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
    audience_config = validated_audience(db, user, data.privacy, data.audience)

    content = data.content.strip()
    if not content and not data.image_url and not data.sticker:
        raise HTTPException(400, "Post cannot be empty")
    media_type = data.media_type or "image"
    if media_type not in {"image", "video", "gif"}:
        raise HTTPException(400, "Invalid media type")
    if media_type == "gif":
        hostname = (urlparse(data.image_url or "").hostname or "").lower()
        if hostname != "giphy.com" and not hostname.endswith(".giphy.com"):
            raise HTTPException(400, "Invalid GIPHY URL")

    post = Post(
        author_id=user.id,
        content=content,
        image_url=data.image_url,
        media_type=media_type,
        sticker=data.sticker,
        privacy=Privacy(data.privacy),
        audience_config=audience_config,
    )

    db.add(post)
    db.flush()
    log_activity(db, user.id, "posts", "post_created", "Created a new post", entity_type="post", entity_id=post.id, details={"privacy": data.privacy, "media_type": media_type})
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
    if post.media_type == "unavailable":
        raise HTTPException(404, "Post not found")
    if post.author_id != user.id:
        raise HTTPException(403, "You can only edit your own posts")

    audience_config = validated_audience(db, user, data.privacy, data.audience)

    content = data.content.strip()
    if not content and not data.image_url and not data.sticker:
        raise HTTPException(400, "Post cannot be empty")
    media_type = data.media_type or post.media_type or "image"
    if media_type not in {"image", "video", "gif"}:
        raise HTTPException(400, "Invalid media type")
    if media_type == "gif":
        hostname = (urlparse(data.image_url or "").hostname or "").lower()
        if hostname != "giphy.com" and not hostname.endswith(".giphy.com"):
            raise HTTPException(400, "Invalid GIPHY URL")

    post.content = content
    post.image_url = data.image_url
    post.media_type = media_type
    post.sticker = data.sticker
    post.privacy = Privacy(data.privacy)
    post.audience_config = audience_config

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
    # Keep a lightweight tombstone while timeline shares still reference this
    # row. This preserves referential integrity and lets every share render the
    # same privacy-safe unavailable state immediately.
    incoming_shares = db.query(Post).filter(Post.shared_post_id == post.id).count()
    if incoming_shares:
        post.content = ""
        post.image_url = None
        post.sticker = None
        post.album_id = None
        post.media_type = "unavailable"
        post.privacy = Privacy.only_me
    else:
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
            log_activity(db, user.id, "posts", "reaction_removed", "Removed a reaction from a post", entity_type="post", entity_id=post.id, target_user_id=post.author_id)
        else:
            like.reaction = data.reaction
            my_reaction = data.reaction
    else:
        db.add(Like(post_id=post_id, user_id=user.id, reaction=data.reaction))
        my_reaction = data.reaction

    if my_reaction:
        log_activity(db, user.id, "posts", "post_reaction", f"Reacted {REACTIONS[my_reaction][0]} to {post.author.name}'s post", entity_type="post", entity_id=post.id, target_user_id=post.author_id, details={"reaction": my_reaction})

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


@router.get("/{post_id}/reactions")
def post_reactions(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post or not can_view(post, db, user):
        raise HTTPException(404, "Post not found")

    rows = (
        db.query(Like, User)
        .join(User, User.id == Like.user_id)
        .filter(Like.post_id == post_id)
        .order_by(Like.created_at.desc(), Like.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "reaction": like.reaction,
                "created_at": like.created_at,
                "user": {
                    "id": reactor.id,
                    "username": reactor.username,
                    "name": reactor.name,
                    "avatar_url": reactor.avatar_url,
                },
            }
            for like, reactor in rows
        ]
    }


@router.post("/{post_id}/comments")
async def comment(
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
    log_activity(db, user.id, "posts", "post_comment", f"Commented on {post.author.name}'s post: {content[:160]}", entity_type="post", entity_id=post.id, target_user_id=post.author_id, details={"comment_id": row.id, "content": content})

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
    await notification_ws.send(post.author_id, {"type": "notification_refresh", "reason": "post_comment"})

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
async def share(
    post_id: int,
    data: PostShareIn = PostShareIn(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    source = db.get(Post, post_id)
    if not source or not can_view(source, db, user):
        raise HTTPException(404, "Post not found")
    # Sharing an existing share always points to the real source, avoiding
    # chains whose privacy rules become ambiguous.
    if source.shared_post_id:
        original = db.get(Post, source.shared_post_id)
        if not original or not can_view(original, db, user):
            raise HTTPException(404, "Original post is no longer available")
        source = original

    destination = data.destination.strip().lower()
    caption = data.caption.strip()
    result = None
    public_distribution = False
    direct_push = None
    group_push = None

    if destination == "feed":
        audience_config = validated_audience(db, user, data.privacy, data.audience)
        shared = Post(author_id=user.id, content=caption,
                      privacy=Privacy(data.privacy), audience_config=audience_config,
                      shared_post_id=source.id)
        db.add(shared)
        db.flush()
        result = shared
        public_distribution = shared.privacy == Privacy.public
        destination_id = shared.id
    elif destination == "group":
        group = db.get(Group, data.target_id) if data.target_id else None
        member = db.query(GroupMember).filter(
            GroupMember.group_id == data.target_id,
            GroupMember.user_id == user.id,
        ).first() if group else None
        if not group or not member:
            raise HTTPException(403, "Join this group before sharing")
        status = "published" if member.role in {"admin", "moderator"} or not group.require_post_approval else "pending"
        group_post = GroupPost(group_id=group.id, author_id=user.id,
                               content=caption, media_url=str(source.id),
                               media_type="shared_post", status=status)
        db.add(group_post)
        db.flush()
        public_distribution = group.privacy == "public" and status == "published"
        destination_id = group_post.id
    elif destination == "messenger":
        from .chat import (blocked_between, conversation_state,
                           direct_recipient_muted, get_or_create_conversation,
                           manager, message_notification_payload,
                           notify_group_message, push_group_message_notifications,
                           serialize_message, set_conversation_state)
        if data.target_type == "group":
            chat_group = db.get(ChatGroup, data.target_id) if data.target_id else None
            member = db.query(ChatGroupMember).filter(
                ChatGroupMember.chat_group_id == data.target_id,
                ChatGroupMember.user_id == user.id,
            ).first() if chat_group else None
            if not chat_group or not member:
                raise HTTPException(403, "You are not a member of this chat")
            message = Message(conversation_id=chat_group.conversation_id,
                              sender_id=user.id, content=caption,
                              message_type="post", attachment_name=str(source.id))
            db.add(message)
            db.flush()
            await notify_group_message(db, chat_group, user, message)
            group_push = (chat_group, message, push_group_message_notifications)
            destination_id = message.id
        else:
            recipient = db.get(User, data.target_id) if data.target_id else None
            if not recipient or blocked_between(db, user.id, recipient.id):
                raise HTTPException(404, "Conversation recipient not found")
            conversation = get_or_create_conversation(db, user.id, recipient.id)
            set_conversation_state(conversation, user.id, "archived", False)
            if recipient.id != user.id:
                set_conversation_state(conversation, recipient.id, "archived", False)
            message = Message(conversation_id=conversation.id, sender_id=user.id,
                              content=caption, message_type="post",
                              attachment_name=str(source.id), is_read=False)
            db.add(message)
            db.flush()
            restricted = conversation_state(conversation, recipient.id)["restricted"]
            muted = direct_recipient_muted(conversation, recipient.id)
            if recipient.id != user.id and not restricted and not muted:
                create_notification(db, user_id=recipient.id, actor_id=user.id,
                                    type="new_message",
                                    message=f"{user.name} shared a post with you",
                                    entity_type="conversation", entity_id=conversation.id)
            payload = {**serialize_message(message, recipient.id, db),
                       "reaction_counts": {}, "my_reaction": None}
            await manager.send_user(user.id, payload)
            if recipient.id != user.id:
                await manager.send_user(recipient.id, payload)
            direct_push = (recipient, conversation, message, restricted, muted,
                           message_notification_payload)
            destination_id = message.id
    else:
        raise HTTPException(400, "Invalid share destination")

    log_activity(db, user.id, "posts", "post_share",
                 f"Shared {source.author.name}'s post to {destination}",
                 entity_type="post", entity_id=source.id,
                 target_user_id=source.author_id,
                 details={"destination": destination, "destination_id": destination_id})
    if public_distribution and source.author_id != user.id:
        create_notification(db, user_id=source.author_id, actor_id=user.id,
                            type="post_share", message=f"{user.name} shared your post",
                            entity_type="post", entity_id=source.id)
    db.commit()
    if group_push:
        chat_group, message, push_notifications = group_push
        await push_notifications(db, chat_group, user, message)
    if direct_push:
        recipient, conversation, message, restricted, muted, make_payload = direct_push
        if recipient.id != user.id and not restricted:
            try:
                await notification_ws.send(recipient.id, make_payload(
                    message, user, conversation_id=conversation.id, silent=muted
                ))
            except Exception:
                pass
    if public_distribution and source.author_id != user.id:
        await notification_ws.send(source.author_id, {"type": "notification_refresh", "reason": "post_share"})
    return {
        "message": "Post shared",
        "destination": destination,
        "destination_id": destination_id,
        "share": serialize(result, db, user) if result else None,
        "shares_count": public_share_count(source.id, db),
    }
