from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.services.rate_limit import RateLimitMiddleware
from app.services.storage import is_managed_media_url
from app.services.uploads import IMAGE_EXTENSIONS, MIB, inspect_upload


def uploaded(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(content))


def test_upload_uses_server_mime_and_signature():
    item = inspect_upload(uploaded("photo.png", b"\x89PNG\r\n\x1a\n" + b"safe"),
                          allowed=IMAGE_EXTENSIONS, max_bytes=MIB)
    assert item.mime == "image/png"
    assert item.category == "image"
    assert item.size == 12


def test_renamed_executable_is_rejected():
    with pytest.raises(HTTPException) as exc:
        inspect_upload(uploaded("not-a-photo.jpg", b"MZ" + b"\x00" * 100),
                       allowed=IMAGE_EXTENSIONS, max_bytes=MIB)
    assert exc.value.status_code == 400


def test_empty_and_oversized_uploads_are_rejected():
    with pytest.raises(HTTPException) as empty:
        inspect_upload(uploaded("empty.png", b""), allowed=IMAGE_EXTENSIONS, max_bytes=MIB)
    assert empty.value.status_code == 400
    with pytest.raises(HTTPException) as large:
        inspect_upload(uploaded("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * 20),
                       allowed=IMAGE_EXTENSIONS, max_bytes=16)
    assert large.value.status_code == 413


def test_only_managed_storage_urls_are_trusted(monkeypatch):
    from app.services import storage as module
    monkeypatch.setattr(module.settings, "s3_public_url", "https://media.example.test/socialn")
    monkeypatch.setattr(module.settings, "cdn_base_url", "")
    assert is_managed_media_url("/uploads/media/photo.jpg")
    assert is_managed_media_url("https://media.example.test/socialn/media/photo.jpg")
    assert not is_managed_media_url("https://attacker.test/photo.jpg")


def test_sensitive_routes_have_stricter_rate_limit_buckets():
    auth_group, auth_limit = RateLimitMiddleware.route_bucket("/api/auth/login", "POST")
    upload_group, upload_limit = RateLimitMiddleware.route_bucket("/api/chat/upload", "POST")
    api_group, api_limit = RateLimitMiddleware.route_bucket("/api/posts/feed", "GET")
    assert auth_group == "auth" and auth_limit < api_limit
    assert upload_group == "upload" and upload_limit < api_limit
    assert api_group == "api"
