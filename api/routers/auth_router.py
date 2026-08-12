from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..db import get_db, User
from ..security import hash_password, verify_password, create_access_token
from ..schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse, DateOfBirthUpdateRequest
from ..deps import get_current_user
from ..rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    user = User(email=body.email, password_hash=hash_password(body.password),
                date_of_birth=body.date_of_birth)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    # Constant-time-ish: always run verify_password even on missing user (or
    # an OAuth-only user with no password_hash, T2-008), against a dummy
    # hash, to reduce user-enumeration via timing (A11).
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    real_hash = user.password_hash if (user and user.password_hash) else dummy_hash
    ok = verify_password(body.password, real_hash)
    if not user or not user.password_hash or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me/date-of-birth", response_model=UserResponse)
def set_date_of_birth(body: DateOfBirthUpdateRequest, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Completes age verification for OAuth-created accounts (T2-008/T2-054),
    which have no date_of_birth until this is called. Also usable by
    password accounts, though RegisterRequest already requires it there."""
    user.date_of_birth = body.date_of_birth
    db.commit()
    db.refresh(user)
    return user
