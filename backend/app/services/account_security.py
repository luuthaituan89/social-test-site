"""Security primitives for revocable sessions and standards-based TOTP."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
import uuid
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from fastapi import Request
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AccountToken, AuthSession, User

REFRESH_COOKIE = "socialn_refresh"
DEVICE_COOKIE = "socialn_device"


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def random_token(size: int = 48) -> str:
    return secrets.token_urlsafe(size)


def device_label(user_agent: str | None) -> str:
    value = (user_agent or "Unknown device")[:160]
    return value or "Unknown device"


def request_device(request: Request) -> tuple[str, str, str | None, str | None]:
    device_id = request.cookies.get(DEVICE_COOKIE) or secrets.token_urlsafe(24)
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return device_id, device_label(user_agent), user_agent, ip_address


def create_session(db: Session, user: User, request: Request) -> tuple[AuthSession, str, bool]:
    device_id, label, user_agent, ip_address = request_device(request)
    known_device = db.query(AuthSession.id).filter(
        AuthSession.user_id == user.id, AuthSession.device_id == device_id
    ).first() is not None
    raw_refresh = random_token()
    now = datetime.utcnow()
    row = AuthSession(
        public_id=str(uuid.uuid4()), user_id=user.id,
        refresh_token_hash=token_hash(raw_refresh), device_id=device_id,
        device_name=label, user_agent=(user_agent or "")[:500] or None,
        ip_address=ip_address, created_at=now, last_seen_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_days),
    )
    db.add(row); db.flush()
    return row, raw_refresh, not known_device


def rotate_refresh(db: Session, raw_refresh: str, request: Request) -> tuple[AuthSession, User, str] | None:
    digest = token_hash(raw_refresh)
    now = datetime.utcnow()
    reused = db.query(AuthSession).filter(AuthSession.previous_token_hash == digest).first()
    if reused:
        db.query(AuthSession).filter(AuthSession.user_id == reused.user_id, AuthSession.revoked_at.is_(None)).update(
            {AuthSession.revoked_at: now, AuthSession.revoke_reason: "refresh_token_reuse"}, synchronize_session=False
        )
        db.commit()
        return None
    row = db.query(AuthSession).filter(AuthSession.refresh_token_hash == digest).first()
    if not row or row.revoked_at is not None or row.expires_at <= now:
        return None
    user = db.get(User, row.user_id)
    if not user or user.account_status != "active":
        return None
    replacement = random_token()
    row.previous_token_hash = row.refresh_token_hash
    row.refresh_token_hash = token_hash(replacement)
    row.last_seen_at = now
    row.ip_address = request.client.host if request.client else row.ip_address
    db.flush()
    return row, user, replacement


def revoke_user_sessions(db: Session, user_id: int, reason: str, except_public_id: str | None = None) -> int:
    query = db.query(AuthSession).filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    if except_public_id:
        query = query.filter(AuthSession.public_id != except_public_id)
    return query.update({AuthSession.revoked_at: datetime.utcnow(), AuthSession.revoke_reason: reason}, synchronize_session=False)


def issue_account_token(db: Session, user_id: int, purpose: str, ttl_minutes: int) -> str:
    now = datetime.utcnow()
    db.query(AccountToken).filter(
        AccountToken.user_id == user_id, AccountToken.purpose == purpose, AccountToken.used_at.is_(None)
    ).update({AccountToken.used_at: now}, synchronize_session=False)
    raw = random_token()
    db.add(AccountToken(user_id=user_id, purpose=purpose, token_hash=token_hash(raw),
                        expires_at=now + timedelta(minutes=ttl_minutes), created_at=now))
    return raw


def consume_account_token(db: Session, raw: str, purpose: str) -> AccountToken | None:
    row = db.query(AccountToken).filter(
        AccountToken.token_hash == token_hash(raw), AccountToken.purpose == purpose,
        AccountToken.used_at.is_(None), AccountToken.expires_at > datetime.utcnow(),
    ).first()
    if row:
        row.used_at = datetime.utcnow()
    return row


def _fernet() -> Fernet:
    material = settings.auth_encryption_key or settings.jwt_secret
    key = base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest())
    return Fernet(key)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(secret: str) -> str:
    return _fernet().decrypt(secret.encode()).decode()


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def totp_code(secret: str, at: int | None = None) -> str:
    counter = int((at if at is not None else time.time()) // 30)
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{number:06d}"


def verify_totp(secret: str, code: str) -> bool:
    clean = code.replace(" ", "").strip()
    now = int(time.time())
    return any(hmac.compare_digest(totp_code(secret, now + drift * 30), clean) for drift in (-1, 0, 1))


def make_recovery_codes() -> tuple[list[str], str]:
    raw = [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(10)]
    stored = json.dumps([token_hash(code) for code in raw])
    return raw, stored


def consume_recovery_code(user: User, code: str) -> bool:
    hashes = json.loads(user.recovery_codes or "[]")
    digest = token_hash(code.strip().lower())
    if digest not in hashes:
        return False
    hashes.remove(digest)
    user.recovery_codes = json.dumps(hashes)
    return True
