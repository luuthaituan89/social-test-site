from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from urllib.parse import urlparse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Post, Like, Comment, User, Privacy, Album, AlbumMedia, Follow,
                      FeedAuthorPreference, FeedPostFeedback, SavedPostCollection, SavedPost,
                      Group, GroupMember, GroupPost, ChatGroup,
                      ChatGroupMember, Message)
from ..schemas import (PostCreate, PostShareIn, CommentCreate, ReactionIn,
                       FeedAuthorPreferenceIn, SavedCollectionIn, SavePostIn)
from ..auth import get_current_user
from ..utils import are_friends, is_blocked_either_way, has_restricted, friend_ids
from ..notifications import create_notification
from .notifications import notification_ws
from ..activity import log_activity
from ..services.privacy import can_view_audience, decode_config, encode_audience_config
from ..services.feed import score_post, diversify, encode_cursor, decode_cursor

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
    author_preference = db.query(FeedAuthorPreference).filter(
        FeedAuthorPreference.user_id == viewer.id,
        FeedAuthorPreference.author_id == post.author_id,
    ).first()
    following = db.query(Follow.id).filter(
        Follow.follower_id == viewer.id,
        Follow.followed_id == post.author_id,
    ).first() is not None
    saved = db.query(SavedPost.id).join(SavedPostCollection).filter(
        SavedPostCollection.user_id == viewer.id,
        SavedPost.post_id == post.id,
    ).first() is not None
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
        "author_following": following,
        "author_favorite": bool(author_preference and author_preference.favorite),
        "author_snoozed": bool(author_preference and author_preference.snoozed_until and author_preference.snoozed_until > datetime.utcnow()),
        "is_saved": saved,
        "likes_count": len(reaction_rows),
        "liked": my_reaction is not None,
        "my_reaction": my_reaction,
        "reaction_counts": reaction_counts,
        "shares_count": public_share_count(post.shared_post_id or post.id, db),
        "comments": [serialize_comment(c) for c in comments],
    }


def _collection(db: Session, user_id: int, collection_id: int | None = None) -> SavedPostCollection:
    if collection_id:
        row = db.query(SavedPostCollection).filter(
            SavedPostCollection.id == collection_id,
            SavedPostCollection.user_id == user_id,
        ).first()
        if not row:
            raise HTTPException(404, "Collection not found")
        return row
    row = db.query(SavedPostCollection).filter(
        SavedPostCollection.user_id == user_id,
        SavedPostCollection.name == "Saved posts",
    ).first()
    if not row:
        row = SavedPostCollection(user_id=user_id, name="Saved posts")
        db.add(row);db.flush()
    return row


@router.get("/feed")
def smart_feed(
    cursor: str | None = None,
    limit: int = Query(default=12, ge=5, le=30),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ranked, privacy-safe feed with an opaque seen-ID cursor."""
    now = datetime.utcnow()
    seen = decode_cursor(cursor)
    friends = friend_ids(db, user.id)
    following = {row[0] for row in db.query(Follow.followed_id).filter(Follow.follower_id == user.id).all()}
    preferences = {row.author_id: row for row in db.query(FeedAuthorPreference).filter(FeedAuthorPreference.user_id == user.id).all()}
    snoozed = {author_id for author_id, pref in preferences.items() if pref.snoozed_until and pref.snoozed_until > now}
    feedback_rows = db.query(FeedPostFeedback).filter(FeedPostFeedback.user_id == user.id).all()
    hidden = {row.post_id for row in feedback_rows if row.hidden or row.show_fewer}
    show_fewer_authors = {post.author_id for row in feedback_rows if row.show_fewer for post in [db.get(Post, row.post_id)] if post}

    rows = db.query(Post).filter(Post.media_type != "unavailable").order_by(Post.created_at.desc(), Post.id.desc()).limit(600).all()
    rows = [row for row in rows if row.id not in seen and row.id not in hidden and row.author_id not in snoozed
            and not has_restricted(db, user.id, row.author_id) and not has_restricted(db, row.author_id, user.id)
            and can_view(row, db, user)]
    ids = [row.id for row in rows]
    reaction_counts = dict(db.query(Like.post_id, func.count(Like.id)).filter(Like.post_id.in_(ids)).group_by(Like.post_id).all()) if ids else {}
    comment_counts = dict(db.query(Comment.post_id, func.count(Comment.id)).filter(Comment.post_id.in_(ids)).group_by(Comment.post_id).all()) if ids else {}
    interacted = {row[0] for row in db.query(Like.post_id).filter(Like.user_id == user.id, Like.post_id.in_(ids)).all()} if ids else set()
    interacted |= {row[0] for row in db.query(Comment.post_id).filter(Comment.author_id == user.id, Comment.post_id.in_(ids)).all()} if ids else set()

    ranked = []
    for post in rows:
        relationship_post = post.author_id == user.id or post.author_id in friends or post.author_id in following
        ranked.append({
            "id": post.id, "post": post, "author_id": post.author_id,
            "shared_post_id": post.shared_post_id,
            "suggested": not relationship_post,
            "score": score_post(
                created_at=post.created_at, reactions=reaction_counts.get(post.id, 0),
                comments=comment_counts.get(post.id, 0), is_friend=post.author_id in friends,
                is_following=post.author_id in following,
                is_favorite=bool(preferences.get(post.author_id) and preferences[post.author_id].favorite),
                viewer_interacted=post.id in interacted,
                show_fewer_author=post.author_id in show_fewer_authors, now=now,
            ),
        })
    primary = sorted((item for item in ranked if not item["suggested"]), key=lambda item: (item["score"], item["id"]), reverse=True)
    recommended = sorted((item for item in ranked if item["suggested"]), key=lambda item: (item["score"], item["id"]), reverse=True)
    # Keep recommendations useful without letting strangers overwhelm the feed.
    suggestions = recommended[:max(2, limit // 5)]
    pool = []
    suggestion_index = 0
    for index, item in enumerate(primary):
        pool.append(item)
        if (index + 1) % 4 == 0 and suggestion_index < len(suggestions):
            pool.append(suggestions[suggestion_index]);suggestion_index += 1
    pool.extend(suggestions[suggestion_index:])
    selected = diversify(pool, limit)
    selected_ids = [item["id"] for item in selected]
    saved_ids = {row[0] for row in db.query(SavedPost.post_id).join(SavedPostCollection).filter(
        SavedPostCollection.user_id == user.id, SavedPost.post_id.in_(selected_ids)).all()} if selected_ids else set()
    items = []
    for item in selected:
        payload = serialize(item["post"], db, user)
        pref = preferences.get(item["author_id"])
        payload.update({
            "feed_score": item["score"],
            "feed_reason": "Suggested for you" if item["suggested"] else ("Favorite" if pref and pref.favorite else "Following" if item["author_id"] in following else "Friend" if item["author_id"] in friends else None),
            "author_following": item["author_id"] in following,
            "author_favorite": bool(pref and pref.favorite),
            "author_snoozed": bool(pref and pref.snoozed_until and pref.snoozed_until > now),
            "is_saved": item["id"] in saved_ids,
        })
        items.append(payload)

    memberships = {row[0] for row in db.query(GroupMember.group_id).filter(GroupMember.user_id == user.id).all()}
    group_query = db.query(Group).filter(Group.privacy == "public", Group.visibility == "visible")
    if memberships:
        group_query = group_query.filter(~Group.id.in_(memberships))
    group_candidates = []
    for group in group_query.order_by(Group.created_at.desc()).limit(40).all():
        members = {row[0] for row in db.query(GroupMember.user_id).filter(GroupMember.group_id == group.id).all()}
        friend_members = len(members & friends)
        group_candidates.append((friend_members * 10 + len(members), group, len(members), friend_members))
    suggested_groups = [{"id": group.id, "name": group.name, "description": group.description,
                         "cover_url": group.cover_url, "member_count": member_count,
                         "friend_members_count": friend_members}
                        for _, group, member_count, friend_members in sorted(
                            group_candidates, key=lambda item: (item[0], item[1].created_at), reverse=True)[:4]]
    all_seen = list(seen) + selected_ids
    remaining = any(item["id"] not in set(all_seen) for item in ranked)
    return {"items": items, "next_cursor": encode_cursor(all_seen) if remaining else None,
            "has_more": remaining, "suggested_groups": suggested_groups}


@router.put("/authors/{author_id}/preference")
def set_author_preference(author_id: int, data: FeedAuthorPreferenceIn,
                          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if author_id == user.id or not db.get(User, author_id):
        raise HTTPException(400, "Invalid author")
    row = db.query(FeedAuthorPreference).filter(
        FeedAuthorPreference.user_id == user.id, FeedAuthorPreference.author_id == author_id).first()
    if not row:
        row = FeedAuthorPreference(user_id=user.id, author_id=author_id);db.add(row)
    if data.favorite is not None:
        row.favorite = data.favorite
    if data.snooze_days is not None:
        row.snoozed_until = (datetime.utcnow() + timedelta(days=data.snooze_days)) if data.snooze_days else None
    row.updated_at = datetime.utcnow();db.commit();db.refresh(row)
    return {"favorite": row.favorite, "snoozed_until": row.snoozed_until}


@router.post("/{post_id}/hide")
def hide_post(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.get(Post, post_id)
    if not post or not can_view(post, db, user): raise HTTPException(404, "Post not found")
    row = db.query(FeedPostFeedback).filter(FeedPostFeedback.user_id == user.id, FeedPostFeedback.post_id == post_id).first()
    if not row: row = FeedPostFeedback(user_id=user.id, post_id=post_id);db.add(row)
    row.hidden = True;db.commit()
    return {"hidden": True}


@router.post("/{post_id}/show-fewer")
def show_fewer(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.get(Post, post_id)
    if not post or not can_view(post, db, user): raise HTTPException(404, "Post not found")
    row = db.query(FeedPostFeedback).filter(FeedPostFeedback.user_id == user.id, FeedPostFeedback.post_id == post_id).first()
    if not row: row = FeedPostFeedback(user_id=user.id, post_id=post_id);db.add(row)
    row.show_fewer = True;db.commit()
    return {"show_fewer": True}


@router.get("/collections")
def collections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(SavedPostCollection).filter(SavedPostCollection.user_id == user.id).order_by(SavedPostCollection.created_at.asc()).all()
    return [{"id": row.id, "name": row.name,
             "posts_count": db.query(SavedPost.id).filter(SavedPost.collection_id == row.id).count()} for row in rows]


@router.post("/collections")
def create_collection(data: SavedCollectionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = data.name.strip()
    exists = db.query(SavedPostCollection).filter(SavedPostCollection.user_id == user.id, func.lower(SavedPostCollection.name) == name.lower()).first()
    if exists: raise HTTPException(409, "A collection with this name already exists")
    row = SavedPostCollection(user_id=user.id, name=name);db.add(row);db.commit();db.refresh(row)
    return {"id": row.id, "name": row.name, "posts_count": 0}


@router.get("/collections/{collection_id}")
def collection_posts(collection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    collection = _collection(db, user.id, collection_id)
    rows = db.query(Post).join(SavedPost, SavedPost.post_id == Post.id).filter(SavedPost.collection_id == collection.id).order_by(SavedPost.saved_at.desc()).all()
    return {"id": collection.id, "name": collection.name,
            "items": [serialize(post, db, user) for post in rows if can_view(post, db, user)]}


@router.post("/{post_id}/save")
def save_post(post_id: int, data: SavePostIn = SavePostIn(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.get(Post, post_id)
    if not post or not can_view(post, db, user): raise HTTPException(404, "Post not found")
    collection = _collection(db, user.id, data.collection_id)
    row = db.query(SavedPost).filter(SavedPost.collection_id == collection.id, SavedPost.post_id == post_id).first()
    if not row: db.add(SavedPost(collection_id=collection.id, post_id=post_id))
    db.commit()
    return {"saved": True, "collection": {"id": collection.id, "name": collection.name}}


@router.delete("/{post_id}/save")
def unsave_post(post_id: int, collection_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    collection_ids = [row[0] for row in db.query(SavedPostCollection.id).filter(SavedPostCollection.user_id == user.id).all()]
    query = db.query(SavedPost).filter(SavedPost.post_id == post_id, SavedPost.collection_id.in_(collection_ids or [-1]))
    if collection_id: query = query.filter(SavedPost.collection_id == collection_id)
    query.delete(synchronize_session=False);db.commit()
    return {"saved": False}


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
