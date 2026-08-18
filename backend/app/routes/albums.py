from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import Album, AlbumMedia, Post, Privacy, User
from ..schemas import AlbumCreate
from ..utils import is_blocked_either_way, friend_ids, has_restricted
from ..services.privacy import (can_view_audience, can_view_profile_field,
                                decode_config, encode_audience_config)

router = APIRouter(prefix="/api/albums", tags=["Albums"])

SYSTEM_ALBUMS = {
    "profile": "Profile pictures",
    "cover": "Cover photos",
    "timeline": "Timeline photos",
}


def album_audience(db: Session, user: User, data: AlbumCreate) -> str | None:
    if data.privacy not in {item.value for item in Privacy}:
        raise HTTPException(400, "Invalid privacy")
    config = data.audience.model_dump()
    selected = set(config["included_ids"]) | set(config["excluded_ids"])
    if selected - friend_ids(db, user.id):
        raise HTTPException(400, "Album audiences can only contain your friends")
    if data.privacy == "specific_friends" and not config["included_ids"]:
        raise HTTPException(400, "Choose at least one specific friend")
    return encode_audience_config(config)


def can_view_album(album: Album, db: Session, viewer: User) -> bool:
    if album.owner_id == viewer.id:
        return True
    if is_blocked_either_way(db, album.owner_id, viewer.id):
        return False
    owner = db.get(User, album.owner_id)
    if not owner or owner.account_status != "active":
        return False
    if not can_view_profile_field(db, owner, viewer.id, "albums"):
        return False
    return can_view_audience(db, owner_id=album.owner_id, viewer_id=viewer.id,
                             audience=album.privacy.value, config=album.audience_config,
                             restricted=has_restricted(db, album.owner_id, viewer.id))


def add_media_once(db: Session, album: Album, url: str | None, media_type: str = "image", caption: str | None = None, privacy: Privacy = Privacy.friends):
    if not url:
        return
    exists = db.query(AlbumMedia).filter(AlbumMedia.album_id == album.id, AlbumMedia.media_url == url).first()
    if not exists:
        db.add(AlbumMedia(album_id=album.id, media_url=url, media_type=media_type, caption=caption, privacy=privacy))
        db.flush()


def ensure_system_albums(db: Session, owner: User):
    albums = {}
    for kind, name in SYSTEM_ALBUMS.items():
        album = db.query(Album).filter(Album.owner_id == owner.id, Album.kind == kind).first()
        if not album:
            album = Album(owner_id=owner.id, kind=kind, name=name, privacy=Privacy.friends)
            db.add(album)
            db.flush()
        albums[kind] = album

    add_media_once(db, albums["profile"], owner.avatar_url, caption="Current profile picture")
    add_media_once(db, albums["cover"], owner.cover_url, caption="Current cover photo")
    posts = db.query(Post).filter(Post.author_id == owner.id, Post.image_url.isnot(None)).all()
    timeline_urls = {post.image_url for post in posts if post.image_url}
    timeline_query = db.query(AlbumMedia).filter(AlbumMedia.album_id == albums["timeline"].id)
    if timeline_urls:
        timeline_query.filter(AlbumMedia.media_url.notin_(timeline_urls)).delete(synchronize_session=False)
    else:
        timeline_query.delete(synchronize_session=False)
    for post in posts:
        add_media_once(db, albums["timeline"], post.image_url, media_type=post.media_type, caption=post.content[:500] if post.content else None, privacy=post.privacy)
        if "profile picture" in (post.content or "").lower():
            add_media_once(db, albums["profile"], post.image_url, caption=post.content[:500])
        if "cover photo" in (post.content or "").lower():
            add_media_once(db, albums["cover"], post.image_url, caption=post.content[:500])
    db.commit()
    return albums


def visible_media(db: Session, album: Album, viewer: User):
    rows = db.query(AlbumMedia).filter(AlbumMedia.album_id == album.id).order_by(AlbumMedia.created_at.desc(), AlbumMedia.id.desc()).all()
    if viewer.id == album.owner_id:
        return rows
    visible = []
    for item in rows:
        post = db.query(Post).filter(Post.author_id == album.owner_id, Post.image_url == item.media_url).first()
        if can_view_audience(db, owner_id=album.owner_id, viewer_id=viewer.id,
                             audience=item.privacy.value,
                             config=post.audience_config if post else album.audience_config,
                             restricted=has_restricted(db, album.owner_id, viewer.id)):
            visible.append(item)
    return visible


def serialize_album(db: Session, album: Album, viewer: User):
    media = visible_media(db, album, viewer)
    return {
        "id": album.id,
        "name": album.name,
        "description": album.description,
        "privacy": album.privacy.value,
        "audience": decode_config(album.audience_config) if album.owner_id == viewer.id else None,
        "kind": album.kind or "custom",
        "created_at": album.created_at,
        "media_count": len(media),
        "cover": media[0].media_url if media else None,
        "cover_type": media[0].media_type if media else None,
    }


@router.get("/user/{user_id}")
def list_albums(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owner = db.get(User, user_id)
    if not owner:
        raise HTTPException(404, "User not found")
    if owner.account_status != "active":
        raise HTTPException(404, "Albums unavailable")
    if owner.id != user.id and is_blocked_either_way(db, owner.id, user.id):
        raise HTTPException(403, "Albums unavailable")
    ensure_system_albums(db, owner)
    rows = db.query(Album).filter(Album.owner_id == owner.id).order_by(Album.kind.is_(None), Album.created_at.asc()).all()
    return [serialize_album(db, row, user) for row in rows if can_view_album(row, db, user)]


@router.post("")
def create_album(data: AlbumCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    audience_config = album_audience(db, user, data)
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Album name is required")
    album = Album(owner_id=user.id, name=name, description=(data.description or "").strip() or None,
                  privacy=Privacy(data.privacy), audience_config=audience_config, kind=None)
    db.add(album)
    db.commit()
    db.refresh(album)
    return serialize_album(db, album, user)


@router.get("/{album_id}")
def get_album(album_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    album = db.get(Album, album_id)
    if not album or not can_view_album(album, db, user):
        raise HTTPException(404, "Album not found")
    owner = db.get(User, album.owner_id)
    if album.kind:
        ensure_system_albums(db, owner)
    media = visible_media(db, album, user)
    result = serialize_album(db, album, user)
    result["owner"] = {"id": owner.id, "name": owner.name, "username": owner.username}
    result["is_owner"] = owner.id == user.id
    result["media"] = [{"id": x.id, "url": x.media_url, "type": x.media_type, "caption": x.caption, "created_at": x.created_at} for x in media]
    return result


@router.put("/{album_id}")
def update_album(album_id: int, data: AlbumCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    album = db.get(Album, album_id)
    if not album or album.owner_id != user.id or album.kind is not None:
        raise HTTPException(404, "Custom album not found")
    audience_config = album_audience(db, user, data)
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Album name is required")
    album.name = name
    album.description = (data.description or "").strip() or None
    album.privacy = Privacy(data.privacy)
    album.audience_config = audience_config
    db.query(AlbumMedia).filter(AlbumMedia.album_id == album.id).update(
        {AlbumMedia.privacy: album.privacy}, synchronize_session=False)
    db.query(Post).filter(Post.author_id == user.id, Post.album_id == album.id).update(
        {Post.privacy: album.privacy, Post.audience_config: album.audience_config}, synchronize_session=False)
    db.commit()
    db.refresh(album)
    return serialize_album(db, album, user)


@router.delete("/{album_id}")
def delete_album(album_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    album = db.get(Album, album_id)
    if not album or album.owner_id != user.id or album.kind is not None:
        raise HTTPException(404, "Custom album not found")
    media_urls = [item.media_url for item in db.query(AlbumMedia).filter(AlbumMedia.album_id == album.id).all()]
    db.query(Post).filter(Post.author_id == user.id, Post.album_id == album.id).delete(synchronize_session=False)
    if media_urls:
        system_ids = [x.id for x in db.query(Album).filter(
            Album.owner_id == user.id, Album.kind.isnot(None)).all()]
        if system_ids:
            db.query(AlbumMedia).filter(
                AlbumMedia.album_id.in_(system_ids), AlbumMedia.media_url.in_(media_urls)
            ).delete(synchronize_session=False)
    db.delete(album)
    db.commit()
    for media_url in media_urls:
        if media_url.startswith("/uploads/album_"):
            (Path(settings.upload_dir) / Path(media_url).name).unlink(missing_ok=True)
    return {"message": "Album and all linked media were deleted"}


@router.post("/{album_id}/media")
async def upload_album_media(album_id: int, file: UploadFile = File(...), caption: str = Form(""),
                             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    album = db.get(Album, album_id)
    if not album or album.owner_id != user.id:
        raise HTTPException(404, "Album not found")
    if album.kind is not None:
        raise HTTPException(400, "Photos can only be added to custom albums")
    suffix = Path(file.filename or "media").suffix.lower()
    image_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    video_ext = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
    if suffix not in image_ext | video_ext:
        raise HTTPException(400, "Only image and video files are allowed")
    filename = f"album_{uuid.uuid4().hex}{suffix}"
    target = Path(settings.upload_dir) / filename
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    row = AlbumMedia(album_id=album.id, media_url=f"/uploads/{filename}",
                     media_type="video" if suffix in video_ext else "image", caption=caption.strip()[:500] or None,
                     privacy=album.privacy)
    db.add(row)
    db.flush()
    media_label = "video" if row.media_type == "video" else "photo"
    db.add(Post(author_id=user.id, content=f"{user.name} added a new {media_label} to the album {album.name}.",
                image_url=row.media_url, media_type=row.media_type, album_id=album.id,
                privacy=album.privacy, audience_config=album.audience_config))
    db.commit()
    db.refresh(row)
    return {"id": row.id, "url": row.media_url, "type": row.media_type, "caption": row.caption, "created_at": row.created_at}


@router.delete("/{album_id}/media/{media_id}")
def delete_album_media(album_id: int, media_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    album = db.get(Album, album_id)
    media = db.get(AlbumMedia, media_id)
    if not album or album.owner_id != user.id or not media or media.album_id != album.id:
        raise HTTPException(404, "Media not found")

    media_url = media.media_url
    if album.kind is not None:
        url = media_url
        if album.kind == "profile" and user.avatar_url == url:
            user.avatar_url = None
        if album.kind == "cover" and user.cover_url == url:
            user.cover_url = None
        db.query(Post).filter(Post.author_id == user.id, Post.image_url == url).delete(synchronize_session=False)
        system_ids = [x.id for x in db.query(Album).filter(Album.owner_id == user.id, Album.kind.isnot(None)).all()]
        db.query(AlbumMedia).filter(AlbumMedia.album_id.in_(system_ids), AlbumMedia.media_url == url).delete(synchronize_session=False)
    else:
        db.query(Post).filter(Post.author_id == user.id, Post.album_id == album.id,
                              Post.image_url == media_url).delete(synchronize_session=False)
        system_ids = [x.id for x in db.query(Album).filter(
            Album.owner_id == user.id, Album.kind.isnot(None)).all()]
        if system_ids:
            db.query(AlbumMedia).filter(
                AlbumMedia.album_id.in_(system_ids), AlbumMedia.media_url == media_url
            ).delete(synchronize_session=False)
        db.delete(media)
    db.commit()
    if album.kind is None and media_url.startswith("/uploads/album_"):
        (Path(settings.upload_dir) / Path(media_url).name).unlink(missing_ok=True)
    return {"message": "Media deleted"}
