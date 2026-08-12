from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..models import User
from ..schemas import RegisterIn, LoginIn, TokenOut, UserPublic
from ..auth import hash_password, verify_password, create_token
from ..activity import log_activity

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(or_(User.email == data.email, User.username == data.username)).first():
        raise HTTPException(400, "Email or username already exists")
    user = User(
        email=data.email,
        username=data.username,
        name=data.name,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()
    log_activity(db, user.id, "security", "account_created", "Created the account", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_token(user.id), user=user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    log_activity(db, user.id, "security", "login", "Logged in to SocialN", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    db.commit()
    return TokenOut(access_token=create_token(user.id), user=user)
