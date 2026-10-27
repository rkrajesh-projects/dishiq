import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from app.db.session import get_db
from app.models.user import User, UserPreference
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory rate limiting for failed login attempts: {email: [timestamp, ...]}
_FAILED_LOGINS: Dict[str, List[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes


def _check_rate_limit(key: str) -> None:
    now = time.time()
    cutoff = now - LOCKOUT_WINDOW_SECONDS
    attempts = [t for t in _FAILED_LOGINS.get(key, []) if t > cutoff]
    _FAILED_LOGINS[key] = attempts
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in 5 minutes.",
        )


def _record_failed_attempt(key: str) -> None:
    now = time.time()
    cutoff = now - LOCKOUT_WINDOW_SECONDS
    attempts = [t for t in _FAILED_LOGINS.get(key, []) if t > cutoff]
    attempts.append(now)
    _FAILED_LOGINS[key] = attempts


def _clear_failed_attempts(key: str) -> None:
    _FAILED_LOGINS.pop(key, None)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")
    full_name: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str


@router.post("/register", response_model=UserRead)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with atomic user preference creation and password strength validation."""
    if len(user_in.password.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name.strip(),
    )
    try:
        db.add(user)
        db.flush()
        
        # Create default user preference in the same atomic transaction
        pref = UserPreference(user_id=user.id)
        db.add(pref)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    
    return UserRead(id=user.id, email=user.email, full_name=user.full_name)


@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """OAuth2 compatible token login with brute-force rate-limiting protection."""
    email_key = form_data.username.strip().lower()
    _check_rate_limit(email_key)

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        _record_failed_attempt(email_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    
    # Login successful: clear any previous failed attempt records
    _clear_failed_attempts(email_key)

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        if hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")
        else 60 * 24 * 8
    )
    
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/logout", summary="Logout User")
def logout():
    """Acknowledge user logout."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
    )
