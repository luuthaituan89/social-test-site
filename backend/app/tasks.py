from io import BytesIO
from pathlib import Path
import json
import logging
import smtplib
from email.message import EmailMessage

from PIL import Image

from .config import settings
from .worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="media.create_thumbnail", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def create_thumbnail(key: str) -> str | None:
    thumb_key = f"thumbnails/{Path(key).stem}.webp"
    if settings.storage_backend.lower() == "s3":
        from .services.storage import S3Storage
        store = S3Storage()
        source = BytesIO()
        store.client.download_fileobj(settings.s3_bucket, key, source)
        source.seek(0)
        with Image.open(source) as image:
            image.thumbnail((960, 960))
            output = BytesIO(); image.convert("RGB").save(output, "WEBP", quality=82); output.seek(0)
        return store.save(output, thumb_key, "image/webp")
    source_path = Path(settings.upload_dir) / key
    target = Path(settings.upload_dir) / thumb_key
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        image.thumbnail((960, 960)); image.convert("RGB").save(target, "WEBP", quality=82)
    return f"/uploads/{thumb_key}"


@celery_app.task(name="media.process_video", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_video(key: str) -> dict:
    """Video pipeline entry point.

    The development stack keeps the original file and records a worker result;
    production can route this task to an FFmpeg/GPU queue without changing the
    request API or storage contract.
    """
    logger.info("video_processing_complete", extra={"key": key, "profile": "original"})
    return {"key": key, "status": "ready", "profile": "original"}


@celery_app.task(name="notifications.dispatch")
def dispatch_notification(user_id: int, payload: dict) -> None:
    from .database import SessionLocal
    from .models import NotificationPreference, PushSubscription

    if not settings.web_push_private_key or not settings.web_push_public_key:
        logger.info("notification_in_app_only", extra={"user_id": user_id, "type": payload.get("type")})
        return
    db = SessionLocal()
    try:
        category = payload.get("category", "other")
        preference = db.query(NotificationPreference).filter_by(user_id=user_id, category=category).first()
        if preference and not preference.web_push:
            return
        from pywebpush import WebPushException, webpush
        stale = []
        for subscription in db.query(PushSubscription).filter_by(user_id=user_id).all():
            try:
                webpush(
                    subscription_info={"endpoint": subscription.endpoint,
                                       "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth}},
                    data=json.dumps(payload, ensure_ascii=False),
                    vapid_private_key=settings.web_push_private_key,
                    vapid_claims={"sub": settings.web_push_subject},
                    ttl=86400,
                )
            except WebPushException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in {404, 410}: stale.append(subscription)
                else: logger.warning("web_push_failed", extra={"user_id": user_id, "status": status})
        for subscription in stale: db.delete(subscription)
        if stale: db.commit()
    finally:
        db.close()


@celery_app.task(name="email.send")
def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.warning("email_not_sent_no_provider", extra={"to": to, "subject": subject, "body_size": len(body)})
        return
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)
    logger.info("email_sent", extra={"to": to, "subject": subject})


@celery_app.task(name="exports.write_json")
def write_data_export(user_id: int, payload: dict) -> str:
    from .services.storage import storage
    raw = BytesIO(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    return storage().save(raw, f"exports/user-{user_id}.json", "application/json")


@celery_app.task(name="accounts.purge_due")
def purge_due_accounts() -> dict:
    """Permanently erase due accounts and their live media.

    Share rows pointing at an authored post become unavailable tombstones before
    the original row is removed, so deleting an account cannot violate the
    shared-post foreign key.
    """
    from datetime import datetime
    from sqlalchemy import or_
    from .database import SessionLocal
    from .models import (Album, AlbumMedia, Group, GroupPost, Message, Post,
                         Privacy, User)
    from .services.storage import delete_media_url

    db = SessionLocal()
    purged, media_deleted = 0, 0
    try:
        users = db.query(User).filter(
            User.account_status == "pending_deletion",
            User.deletion_scheduled_for.isnot(None),
            User.deletion_scheduled_for <= datetime.utcnow(),
        ).all()
        for user in users:
            user_id = user.id
            post_ids = [row.id for row in db.query(Post.id).filter(Post.author_id == user.id).all()]
            urls = {value for value in (user.avatar_url, user.cover_url) if value}
            urls.update(row.image_url for row in db.query(Post.image_url).filter(
                Post.author_id == user.id, Post.image_url.isnot(None)).all())
            urls.update(row.attachment_url for row in db.query(Message.attachment_url).filter(
                Message.sender_id == user.id, Message.attachment_url.isnot(None)).all())
            album_ids = [row.id for row in db.query(Album.id).filter(Album.owner_id == user.id).all()]
            if album_ids:
                urls.update(row.media_url for row in db.query(AlbumMedia.media_url).filter(
                    AlbumMedia.album_id.in_(album_ids)).all())
            owned_group_ids = [row.id for row in db.query(Group.id).filter(Group.owner_id == user.id).all()]
            urls.update(row.cover_url for row in db.query(Group.cover_url).filter(
                Group.owner_id == user.id, Group.cover_url.isnot(None)).all())
            group_media = db.query(GroupPost.media_url).filter(
                GroupPost.media_url.isnot(None),
                or_(GroupPost.author_id == user.id,
                    GroupPost.group_id.in_(owned_group_ids) if owned_group_ids else False),
            ).all()
            urls.update(row.media_url for row in group_media)
            if post_ids:
                db.query(Post).filter(Post.shared_post_id.in_(post_ids)).update({
                    Post.shared_post_id: None, Post.media_type: "unavailable",
                    Post.image_url: None, Post.sticker: None, Post.privacy: Privacy.only_me,
                }, synchronize_session=False)
            for url in urls:
                try:
                    media_deleted += int(delete_media_url(url))
                except Exception:
                    logger.exception("account_media_delete_failed", extra={"user_id": user_id, "url": url})
                    # Keep the account tombstone and URL references so the next
                    # periodic run can retry instead of silently orphaning data.
                    db.rollback()
                    raise
            db.delete(user)
            db.commit()
            purged += 1
        return {"purged_accounts": purged, "deleted_media": media_deleted}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
