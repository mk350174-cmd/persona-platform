"""API key issuance/listing/revocation (T2-010). Keys are stored only as a
SHA-256 hash — the raw key is returned once, at creation, and never again."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db, APIKey, User
from ..deps import get_current_user
from ..schemas import ApiKeyCreateResponse, ApiKeyResponse
from ..security import generate_api_key

router = APIRouter(prefix="/apikeys", tags=["api-keys"])


@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw_key, key_hash, preview = generate_api_key()
    record = APIKey(user_id=user.id, key_hash=key_hash, key_preview=preview)
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiKeyCreateResponse(id=record.id, api_key=raw_key, key_preview=preview)


@router.get("/", response_model=list[ApiKeyResponse])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(APIKey).filter(APIKey.user_id == user.id).order_by(APIKey.created_at.desc()).all()


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user.id).first()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    record.revoked = True
    db.commit()
