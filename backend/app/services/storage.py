from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
import shutil

import boto3

from ..config import settings


class LocalStorage:
    def save(self, source: BinaryIO, key: str, content_type: str | None = None) -> str:
        target = Path(settings.upload_dir) / key
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as output:
            shutil.copyfileobj(source, output)
        return f"/uploads/{key}"

    def delete(self, key: str) -> None:
        target = (Path(settings.upload_dir) / key).resolve()
        root = Path(settings.upload_dir).resolve()
        if target != root and root in target.parents:
            target.unlink(missing_ok=True)


class S3Storage:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
        )

    def save(self, source: BinaryIO, key: str, content_type: str | None = None) -> str:
        extra = {"ContentType": content_type} if content_type else None
        self.client.upload_fileobj(source, settings.s3_bucket, key, ExtraArgs=extra or {})
        base = (settings.cdn_base_url or settings.s3_public_url).rstrip("/")
        return f"{base}/{key}"

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=settings.s3_bucket, Key=key)


def storage():
    return S3Storage() if settings.storage_backend.lower() == "s3" else LocalStorage()


def is_managed_media_url(url: str | None) -> bool:
    if not url:
        return False
    if url.startswith("/uploads/"):
        return True
    return any(bool(base) and url.startswith(base.rstrip("/") + "/")
               for base in (settings.s3_public_url, settings.cdn_base_url))


def delete_media_url(url: str | None) -> bool:
    if not url:
        return False
    if url.startswith("/uploads/"):
        LocalStorage().delete(url.removeprefix("/uploads/"))
        return True
    for base in (settings.s3_public_url, settings.cdn_base_url):
        prefix = (base or "").rstrip("/") + "/"
        if prefix != "/" and url.startswith(prefix):
            S3Storage().delete(url[len(prefix):])
            return True
    return False
