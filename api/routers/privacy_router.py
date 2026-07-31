"""GDPR data-portability export + right-to-erasure (T2-053).

Scope: this covers the data this repo's own database holds. It does not
reach into Stripe's own records (a real deletion request there is a
separate, Stripe-side action) or persona_mcp's cache directory (that's a
CEID-scoring cache keyed by persona, not by user, so it holds no
identifiable data to erase)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..db import get_db, User, Purchase, ChatMessage, APIKey
from ..deps import get_current_user
from ..schemas import DataExportResponse

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/data-export", response_model=DataExportResponse)
def export_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    purchases = db.query(Purchase).filter(Purchase.user_id == user.id).all()
    messages = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).all()
    keys = db.query(APIKey).filter(APIKey.user_id == user.id).all()
    return DataExportResponse(
        user=user, date_of_birth=user.date_of_birth,
        purchases=purchases, chat_messages=messages, api_keys=keys,
    )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Right to erasure. Deletes chat messages, API keys, purchase records,
    and the user row itself. Irreversible — there is no soft-delete/undo."""
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.query(APIKey).filter(APIKey.user_id == user.id).delete()
    db.query(Purchase).filter(Purchase.user_id == user.id).delete()
    db.delete(user)
    db.commit()
