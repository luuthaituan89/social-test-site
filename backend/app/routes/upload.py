from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from ..auth import get_current_user
from ..models import User
from ..config import settings
from ..services.uploads import GENERAL_EXTENSIONS, MIB, save_validated_upload
from ..tasks import create_thumbnail, process_video

router = APIRouter(prefix="/api", tags=["Upload"])

@router.post("/upload")
def upload(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    del user
    url, inspection, filename = save_validated_upload(
        file, prefix="media", allowed=GENERAL_EXTENSIONS,
        max_bytes=settings.max_file_upload_mb * MIB,
        category_limits={"image": settings.max_image_upload_mb * MIB,
                         "video": settings.max_video_upload_mb * MIB},
    )
    thumbnail_url = None
    if inspection.category == "image" and inspection.suffix != ".gif":
        base = (settings.cdn_base_url or settings.s3_public_url).rstrip("/")
        from pathlib import Path
        thumbnail_url = f"{base}/thumbnails/{Path(filename).stem}.webp" if settings.storage_backend.lower() == "s3" else f"/uploads/thumbnails/{Path(filename).stem}.webp"
        try:
            create_thumbnail.delay(filename)
        except Exception:
            # Upload remains successful when the optional worker is unavailable.
            thumbnail_url = None
    elif inspection.category == "video":
        try:
            process_video.delay(filename)
        except Exception:
            pass
    return {"url": url, "thumbnail_url": thumbnail_url, "storage": settings.storage_backend,
            "mime": inspection.mime, "size": inspection.size, "media_type": inspection.category}
