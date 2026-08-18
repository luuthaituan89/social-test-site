from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pathlib import Path
import uuid
from ..auth import get_current_user
from ..models import User
from ..config import settings
from ..services.storage import storage
from ..tasks import create_thumbnail, process_video

router = APIRouter(prefix="/api", tags=["Upload"])

@router.post("/upload")
def upload(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    allowed = {
        ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic",
        ".mp4", ".webm", ".mov", ".mkv", ".avi",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".csv", ".rtf", ".odt", ".ods", ".zip", ".rar", ".7z",
    }
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, "Unsupported image, video, document, or archive format")
    filename = f"media/{uuid.uuid4().hex}{suffix}"
    url = storage().save(file.file, filename, file.content_type)
    thumbnail_url = None
    if (file.content_type or "").startswith("image/") and suffix != ".gif":
        base = (settings.cdn_base_url or settings.s3_public_url).rstrip("/")
        thumbnail_url = f"{base}/thumbnails/{Path(filename).stem}.webp" if settings.storage_backend.lower() == "s3" else f"/uploads/thumbnails/{Path(filename).stem}.webp"
        try:
            create_thumbnail.delay(filename)
        except Exception:
            # Upload remains successful when the optional worker is unavailable.
            thumbnail_url = None
    elif (file.content_type or "").startswith("video/"):
        try:
            process_video.delay(filename)
        except Exception:
            pass
    return {"url": url, "thumbnail_url": thumbnail_url, "storage": settings.storage_backend}
