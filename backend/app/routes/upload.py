from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pathlib import Path
import uuid, shutil
from ..auth import get_current_user
from ..models import User
from ..config import settings

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
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = Path(settings.upload_dir) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/uploads/{filename}"}
