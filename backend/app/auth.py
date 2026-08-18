from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import AuthSession, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_token(user_id: int, session_id: str, auth_version: int = 1) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "sid": session_id, "ver": auth_version,
                       "type": "access", "iat": now, "exp": expire,
                       "iss": "socialn", "aud": "socialn-web"}, settings.jwt_secret, algorithm="HS256")


def create_login_challenge(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "type": "login_challenge", "iat": now,
                       "exp": now + timedelta(minutes=5), "iss": "socialn", "aud": "socialn-web"},
                      settings.jwt_secret, algorithm="HS256")


def decode_login_challenge(token: str) -> int:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience="socialn-web", issuer="socialn")
    if payload.get("type") != "login_challenge":
        raise JWTError("Wrong token type")
    return int(payload["sub"])


def authenticated_user_from_token(db: Session, token: str) -> tuple[User, AuthSession]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience="socialn-web", issuer="socialn")
    if payload.get("type") != "access":
        raise JWTError("Wrong token type")
    user = db.get(User, int(payload.get("sub")))
    session = db.query(AuthSession).filter(AuthSession.public_id == payload.get("sid")).first()
    if (not user or user.account_status != "active" or int(payload.get("ver", 0)) != user.auth_version
            or not session or session.user_id != user.id or session.revoked_at is not None
            or session.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)):
        raise JWTError("Session revoked")
    return user, session


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user, _ = authenticated_user_from_token(db, token)
    except (JWTError, TypeError, ValueError):
        raise credentials_error
    return user
