"""Auth dependency shared by all routers."""

from fastapi import HTTPException, Depends, Header
from sqlalchemy.orm import Session

from api.db import get_db, get_user_by_api_key, User


def get_current_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    user = get_user_by_api_key(db, x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return user
