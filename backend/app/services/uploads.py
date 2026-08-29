"""Central upload validation used by posts, profiles, albums and chat.

Browser supplied filenames and Content-Type headers are hints only.  This module
checks size and file signatures before an object is persisted, and always writes
with a server-selected MIME type.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable
import mimetypes
import uuid

from fastapi import HTTPException, UploadFile

from .storage import storage


MIB = 1024 * 1024

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".rtf", ".odt", ".ods", ".zip", ".rar", ".7z",
}
GENERAL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | DOCUMENT_EXTENSIONS
CHAT_EXTENSIONS = GENERAL_EXTENSIONS | AUDIO_EXTENSIONS

SERVER_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
    ".heic": "image/heic", ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".m4v": "video/x-m4v", ".webm": "video/webm", ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".pdf": "application/pdf",
    ".doc": "application/msword", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain", ".csv": "text/csv", ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text", ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".zip": "application/zip", ".rar": "application/vnd.rar", ".7z": "application/x-7z-compressed",
}


@dataclass(frozen=True)
class UploadInspection:
    suffix: str
    size: int
    mime: str
    category: str


def _size_and_head(stream: BinaryIO, head_size: int = 8192) -> tuple[int, bytes]:
    try:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(0)
        head = stream.read(head_size)
        stream.seek(0)
        return size, head
    except (AttributeError, OSError) as exc:
        raise HTTPException(400, "The uploaded file could not be inspected") from exc


def _has_expected_signature(suffix: str, head: bytes) -> bool:
    if suffix in {".txt", ".csv"}:
        if b"\x00" in head:
            return False
        try:
            head.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    if suffix == ".rtf": return head.startswith(b"{\\rtf")
    if suffix in {".jpg", ".jpeg"}: return head.startswith(b"\xff\xd8\xff")
    if suffix == ".png": return head.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix == ".gif": return head.startswith((b"GIF87a", b"GIF89a"))
    if suffix == ".bmp": return head.startswith(b"BM")
    if suffix == ".webp": return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    if suffix in {".mp4", ".mov", ".m4v", ".heic"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"
    if suffix in {".webm", ".mkv"}: return head.startswith(b"\x1aE\xdf\xa3")
    if suffix == ".avi": return head.startswith(b"RIFF") and head[8:12] == b"AVI "
    if suffix == ".wav": return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if suffix == ".ogg": return head.startswith(b"OggS")
    if suffix == ".mp3": return head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    if suffix == ".m4a": return len(head) >= 12 and head[4:8] == b"ftyp"
    if suffix == ".pdf": return head.startswith(b"%PDF-")
    if suffix in {".docx", ".xlsx", ".pptx", ".odt", ".ods", ".zip"}: return head.startswith(b"PK")
    if suffix in {".doc", ".xls", ".ppt"}: return head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if suffix == ".rar": return head.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"))
    if suffix == ".7z": return head.startswith(b"7z\xbc\xaf'\x1c")
    return False


def inspect_upload(upload: UploadFile, *, allowed: Iterable[str], max_bytes: int) -> UploadInspection:
    suffix = Path(upload.filename or "").suffix.lower()
    allowed_set = {value.lower() for value in allowed}
    if suffix not in allowed_set:
        raise HTTPException(400, "This file type is not allowed")
    size, head = _size_and_head(upload.file)
    if size <= 0:
        raise HTTPException(400, "The uploaded file is empty")
    if size > max_bytes:
        raise HTTPException(413, f"File must be {max_bytes // MIB} MB or smaller")
    if not _has_expected_signature(suffix, head):
        raise HTTPException(400, "File contents do not match the selected file type")
    category = "image" if suffix in IMAGE_EXTENSIONS else "video" if suffix in VIDEO_EXTENSIONS else "voice" if suffix in AUDIO_EXTENSIONS else "file"
    mime = SERVER_MIME.get(suffix) or mimetypes.types_map.get(suffix) or "application/octet-stream"
    return UploadInspection(suffix=suffix, size=size, mime=mime, category=category)


def save_validated_upload(upload: UploadFile, *, prefix: str, allowed: Iterable[str], max_bytes: int,
                          category_limits: dict[str, int] | None = None) -> tuple[str, UploadInspection, str]:
    inspection = inspect_upload(upload, allowed=allowed, max_bytes=max_bytes)
    category_limit = (category_limits or {}).get(inspection.category)
    if category_limit is not None and inspection.size > category_limit:
        raise HTTPException(413, f"{inspection.category.title()} must be {category_limit // MIB} MB or smaller")
    key = f"{prefix.strip('/')}/{uuid.uuid4().hex}{inspection.suffix}"
    upload.file.seek(0)
    url = storage().save(upload.file, key, inspection.mime)
    return url, inspection, key
