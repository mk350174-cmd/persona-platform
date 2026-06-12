"""
File upload endpoints — user avatars, compiled configs.

Uses Supabase Storage for cloud file hosting.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from api.db import get_db, User
from api.auth import get_current_user
from api.storage import get_storage_manager, is_storage_available
from api.observability import track_event, get_structured_logger

router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = get_structured_logger("uploads_router")


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload user avatar.

    Accepts: PNG, JPG, WebP (max 5 MB)
    Returns: Public URL to avatar
    """
    # Validate file type
    if file.content_type not in ["image/png", "image/jpeg", "image/webp"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Accepted: PNG, JPG, WebP",
        )

    # Validate file size (5 MB limit)
    max_size = 5 * 1024 * 1024
    file_content = file.file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {max_size // 1024 // 1024} MB)",
        )

    # Upload to Supabase Storage
    storage = get_storage_manager()
    if not storage.is_available():
        raise HTTPException(
            status_code=503,
            detail="File storage service unavailable. Try again later.",
        )

    avatar_url = storage.upload_avatar(str(user.id), file_content, file.content_type)
    if not avatar_url:
        logger.error(f"Avatar upload failed for user {user.id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload avatar. Try again later.",
        )

    # Update user avatar URL in database
    user.avatar_url = avatar_url
    db.commit()

    # Track upload event
    track_event(
        "avatar_uploaded",
        str(user.id),
        properties={"file_size_bytes": len(file_content)},
    )

    logger.info(f"Avatar uploaded for user {user.id}", avatar_url=avatar_url)

    return {
        "avatar_url": avatar_url,
        "size_bytes": len(file_content),
        "message": "Avatar uploaded successfully",
    }


@router.post("/compiled-config/{persona_id}")
def upload_compiled_config(
    persona_id: str,
    platform: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload compiled persona config (JSON).

    Stores in private bucket with signed download URL (valid 1 hour).
    """
    # Validate content type
    if file.content_type != "application/json":
        raise HTTPException(
            status_code=400,
            detail="File must be JSON (application/json)",
        )

    # Validate file size
    max_size = 10 * 1024 * 1024  # 10 MB
    file_content = file.file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File too large (max 10 MB)",
        )

    # Validate platform
    valid_platforms = ["ios", "android", "web", "windows", "macos"]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Accepted: {', '.join(valid_platforms)}",
        )

    # Upload to Supabase Storage
    storage = get_storage_manager()
    if not storage.is_available():
        raise HTTPException(
            status_code=503,
            detail="File storage service unavailable",
        )

    download_url = storage.upload_compiled_config(
        str(user.id),
        persona_id,
        platform,
        file_content,
    )
    if not download_url:
        logger.error(f"Config upload failed for user {user.id}, persona {persona_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload config",
        )

    # Track upload event
    track_event(
        "config_uploaded",
        str(user.id),
        properties={
            "persona_id": persona_id,
            "platform": platform,
            "file_size_bytes": len(file_content),
        },
    )

    logger.info(
        f"Compiled config uploaded",
        user_id=user.id,
        persona_id=persona_id,
        platform=platform,
    )

    return {
        "download_url": download_url,
        "persona_id": persona_id,
        "platform": platform,
        "size_bytes": len(file_content),
        "expires_in_seconds": 3600,
        "message": "Config uploaded successfully",
    }


@router.delete("/avatar")
def delete_avatar(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete user's avatar."""
    storage = get_storage_manager()
    if not storage.is_available():
        raise HTTPException(
            status_code=503,
            detail="Storage service unavailable",
        )

    # Delete avatar file
    if storage.delete_file("user-avatars", f"avatars/{user.id}/profile.png"):
        user.avatar_url = None
        db.commit()

        track_event("avatar_deleted", str(user.id))
        return {"message": "Avatar deleted"}

    raise HTTPException(
        status_code=500,
        detail="Failed to delete avatar",
    )


@router.get("/status")
def storage_status():
    """Check if file storage is available."""
    return {
        "storage_available": is_storage_available(),
        "service": "Supabase Storage",
    }
