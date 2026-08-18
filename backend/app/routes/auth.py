from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from jose import JWTError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..activity import log_activity
from ..auth import (authenticated_user_from_token, create_login_challenge, create_token,
                    decode_login_challenge, hash_password, oauth2_scheme, verify_password)
from ..config import settings
from ..database import get_db
from ..models import AuthSession, Notification, User
from ..schemas import (LoginIn, LoginResult, PasswordConfirm, PasswordResetConfirm,
                       PasswordResetRequest, RegisterIn, TokenConfirm, TokenOut,
                       TwoFactorConfirm, TwoFactorLoginIn)
from ..services.account_security import (DEVICE_COOKIE, REFRESH_COOKIE, consume_account_token,
                                         consume_recovery_code, create_session, decrypt_secret,
                                         encrypt_secret, issue_account_token, make_recovery_codes,
                                         new_totp_secret, request_device, revoke_user_sessions,
                                         rotate_refresh, verify_totp)
from ..tasks import send_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _set_auth_cookies(response: Response, request: Request, refresh: str, device_id: str | None = None) -> None:
    device_id = device_id or request_device(request)[0]
    common = {"secure": settings.auth_cookie_secure, "samesite": "lax"}
    response.set_cookie(REFRESH_COOKIE, refresh, httponly=True, max_age=settings.refresh_token_days * 86400,
                        path="/api/auth", **common)
    response.set_cookie(DEVICE_COOKIE, device_id, httponly=True, max_age=365 * 86400, path="/", **common)


def _clear_refresh(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth", secure=settings.auth_cookie_secure, samesite="lax")


def _mail(to: str, subject: str, body: str) -> None:
    try:
        send_email.delay(to, subject, body)
    except Exception:
        send_email(to, subject, body)


def _finish_login(user: User, request: Request, response: Response, db: Session) -> LoginResult:
    session, refresh, new_device = create_session(db, user, request)
    if new_device:
        db.add(Notification(user_id=user.id, actor_id=None, type="security_alert",
                            message=f"New login from {session.device_name}", entity_type="auth_session"))
        _mail(user.email, "New SocialN login", f"A new login was detected from {session.device_name}. IP: {session.ip_address or 'unknown'}")
        log_activity(db, user.id, "security", "new_device_login", "Signed in from a new device",
                     ip_address=session.ip_address, user_agent=session.user_agent)
    db.commit()
    _set_auth_cookies(response, request, refresh, session.device_id)
    return LoginResult(access_token=create_token(user.id, session.public_id, user.auth_version), user=user,
                       expires_in=settings.jwt_expire_minutes * 60,
                       verification_required=user.email_verified_at is None)


def _current_context(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        return authenticated_user_from_token(db, token)
    except (JWTError, TypeError, ValueError):
        raise HTTPException(401, "Invalid, expired or revoked session")


@router.post("/register", response_model=LoginResult)
def register(data: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(or_(User.email == data.email, User.username == data.username)).first():
        raise HTTPException(400, "Email or username already exists")
    user = User(email=data.email, username=data.username, name=data.name, password_hash=hash_password(data.password))
    db.add(user); db.flush()
    raw = issue_account_token(db, user.id, "verify_email", 8 * 60)
    _mail(user.email, "Verify your SocialN email", f"Open this link within 8 hours: {settings.frontend_url}/?verify_email={quote(raw)}")
    log_activity(db, user.id, "security", "account_created", "Created the account",
                 ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    return _finish_login(user, request, response, db)


@router.post("/login", response_model=LoginResult)
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if (user.account_status == "pending_deletion" and user.deletion_scheduled_for
            and user.deletion_scheduled_for <= datetime.utcnow()):
        raise HTTPException(410, "The account recovery period has ended")
    if settings.require_verified_email and user.email_verified_at is None:
        raise HTTPException(403, "Verify your email before signing in")
    if user.totp_enabled:
        return LoginResult(requires_2fa=True, challenge_token=create_login_challenge(user.id))
    if user.account_status in {"deactivated", "pending_deletion"}:
        user.account_status = "active"; user.deactivated_at = None
        user.deletion_requested_at = None; user.deletion_scheduled_for = None
        log_activity(db, user.id, "security", "account_recovered", "Recovered and reactivated the account")
    log_activity(db, user.id, "security", "login", "Logged in to SocialN",
                 ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    return _finish_login(user, request, response, db)


@router.post("/login/2fa", response_model=LoginResult)
def login_two_factor(data: TwoFactorLoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    try: user = db.get(User, decode_login_challenge(data.challenge_token))
    except Exception: raise HTTPException(401, "The login challenge expired")
    if not user or not user.totp_enabled or not user.totp_secret_encrypted:
        raise HTTPException(401, "Two-factor authentication is unavailable")
    valid = verify_totp(decrypt_secret(user.totp_secret_encrypted), data.code)
    if not valid: valid = consume_recovery_code(user, data.code)
    if not valid:
        log_activity(db, user.id, "security", "two_factor_failed", "Rejected an invalid two-factor code"); db.commit()
        raise HTTPException(401, "Invalid authentication code")
    if user.account_status in {"deactivated", "pending_deletion"}:
        user.account_status = "active"; user.deactivated_at = None
        user.deletion_requested_at = None; user.deletion_scheduled_for = None
        log_activity(db, user.id, "security", "account_recovered", "Recovered and reactivated the account")
    log_activity(db, user.id, "security", "login_2fa", "Completed two-factor authentication")
    return _finish_login(user, request, response, db)


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db),
            refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE)):
    if not refresh_cookie: raise HTTPException(401, "Refresh session not found")
    result = rotate_refresh(db, refresh_cookie, request)
    if not result:
        _clear_refresh(response); raise HTTPException(401, "Refresh session expired, revoked or reused")
    session, user, replacement = result
    db.commit(); _set_auth_cookies(response, request, replacement, session.device_id)
    return TokenOut(access_token=create_token(user.id, session.public_id, user.auth_version), user=user,
                    expires_in=settings.jwt_expire_minutes * 60, verification_required=user.email_verified_at is None)


@router.post("/logout")
def logout(response: Response, context=Depends(_current_context), db: Session = Depends(get_db)):
    _, session = context; session.revoked_at = datetime.utcnow(); session.revoke_reason = "logout"
    db.commit(); _clear_refresh(response); return {"message": "Logged out"}


@router.post("/logout-all")
def logout_all(response: Response, context=Depends(_current_context), db: Session = Depends(get_db)):
    user, _ = context; revoke_user_sessions(db, user.id, "logout_all"); user.auth_version += 1
    db.commit(); _clear_refresh(response); return {"message": "All devices have been logged out"}


@router.get("/sessions")
def sessions(context=Depends(_current_context), db: Session = Depends(get_db)):
    user, current = context
    rows = db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None),
                                        AuthSession.expires_at > datetime.utcnow()).order_by(AuthSession.last_seen_at.desc()).all()
    return [{"id": row.public_id, "device_name": row.device_name, "ip_address": row.ip_address,
             "created_at": row.created_at, "last_seen_at": row.last_seen_at,
             "expires_at": row.expires_at, "current": row.id == current.id} for row in rows]


@router.delete("/sessions/{public_id}")
def revoke_session(public_id: str, response: Response, context=Depends(_current_context), db: Session = Depends(get_db)):
    user, current = context
    row = db.query(AuthSession).filter(AuthSession.public_id == public_id, AuthSession.user_id == user.id).first()
    if not row: raise HTTPException(404, "Session not found")
    row.revoked_at = datetime.utcnow(); row.revoke_reason = "user_revoked"; db.commit()
    if row.id == current.id: _clear_refresh(response)
    return {"message": "Device session revoked", "current": row.id == current.id}


@router.post("/email/resend")
def resend_verification(context=Depends(_current_context), db: Session = Depends(get_db)):
    user, _ = context
    if user.email_verified_at: return {"message": "Email is already verified"}
    raw = issue_account_token(db, user.id, "verify_email", 8 * 60); db.commit()
    _mail(user.email, "Verify your SocialN email", f"Open this link within 8 hours: {settings.frontend_url}/?verify_email={quote(raw)}")
    return {"message": "Verification email sent"}


@router.post("/email/verify")
def verify_email(data: TokenConfirm, db: Session = Depends(get_db)):
    token = consume_account_token(db, data.token, "verify_email")
    if not token: raise HTTPException(400, "Verification link is invalid or expired")
    user = db.get(User, token.user_id); user.email_verified_at = datetime.utcnow()
    log_activity(db, user.id, "security", "email_verified", "Verified the account email")
    db.commit(); return {"message": "Email verified successfully"}


@router.post("/forgot-password")
def forgot_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        raw = issue_account_token(db, user.id, "reset_password", 30); db.commit()
        _mail(user.email, "Reset your SocialN password", f"Open this link within 30 minutes: {settings.frontend_url}/?reset_password={quote(raw)}")
    return {"message": "If that email belongs to an account, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    token = consume_account_token(db, data.token, "reset_password")
    if not token: raise HTTPException(400, "Reset link is invalid or expired")
    user = db.get(User, token.user_id); user.password_hash = hash_password(data.new_password); user.auth_version += 1
    revoke_user_sessions(db, user.id, "password_reset")
    log_activity(db, user.id, "security", "password_reset", "Reset the account password")
    db.commit(); _mail(user.email, "SocialN password changed", "Your SocialN password was reset. If this was not you, contact support immediately.")
    return {"message": "Password reset successfully. Sign in with your new password"}


@router.post("/2fa/setup")
def setup_two_factor(data: PasswordConfirm, context=Depends(_current_context), db: Session = Depends(get_db)):
    user, _ = context
    if not verify_password(data.password, user.password_hash): raise HTTPException(400, "Password is incorrect")
    secret = new_totp_secret(); user.totp_secret_encrypted = encrypt_secret(secret); user.totp_enabled = False; db.commit()
    label = quote(f"SocialN:{user.email}"); issuer = quote("SocialN")
    return {"secret": secret, "otpauth_url": f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&digits=6&period=30"}


@router.post("/2fa/confirm")
def confirm_two_factor(data: TwoFactorConfirm, context=Depends(_current_context), db: Session = Depends(get_db)):
    user, _ = context
    if not user.totp_secret_encrypted or not verify_totp(decrypt_secret(user.totp_secret_encrypted), data.code):
        raise HTTPException(400, "Invalid authentication code")
    codes, stored = make_recovery_codes(); user.recovery_codes = stored; user.totp_enabled = True
    log_activity(db, user.id, "security", "two_factor_enabled", "Enabled two-factor authentication")
    db.commit(); return {"message": "Two-factor authentication enabled", "recovery_codes": codes}


@router.post("/2fa/disable")
def disable_two_factor(data: PasswordConfirm, response: Response, context=Depends(_current_context), db: Session = Depends(get_db)):
    user, _ = context
    if not verify_password(data.password, user.password_hash): raise HTTPException(400, "Password is incorrect")
    user.totp_enabled = False; user.totp_secret_encrypted = None; user.recovery_codes = None; user.auth_version += 1
    revoke_user_sessions(db, user.id, "two_factor_disabled")
    log_activity(db, user.id, "security", "two_factor_disabled", "Disabled two-factor authentication")
    db.commit(); _clear_refresh(response)
    return {"message": "Two-factor authentication disabled. Sign in again"}
