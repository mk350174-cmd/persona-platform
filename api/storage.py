"""
Supabase Storage integration for file uploads.

Handles:
- User avatar uploads (public access)
- Persona assets (public access)
- Compiled configs (private, signed URLs)
"""

import os
from typing import Optional
from pathlib import Path

try:
    from supabase import create_client, Client
except ImportError:
    Client = None


class StorageManager:
    """Manage file uploads to Supabase Storage."""

    def __init__(self):
        """Initialize Supabase client."""
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.client: Optional[Client] = None

        if self.supabase_url and self.service_role_key:
            try:
                self.client = create_client(self.supabase_url, self.service_role_key)
            except Exception as e:
                import logging
                logging.warning(f"Failed to initialize Supabase Storage: {e}")

    def is_available(self) -> bool:
        """Check if Supabase Storage is configured and available."""
        return self.client is not None

    def upload_avatar(self, user_id: str, file_bytes: bytes, content_type: str = "image/png") -> Optional[str]:
        """
        Upload user avatar and return public URL.

        Args:
            user_id: User ID
            file_bytes: Image bytes (PNG, JPG, etc.)
            content_type: MIME type (e.g., 'image/png')

        Returns:
            Public URL to the avatar, or None if upload failed
        """
        if not self.is_available():
            return None

        try:
            bucket = "user-avatars"
            path = f"avatars/{user_id}/profile.png"

            # Upload file to Supabase Storage
            self.client.storage.from_(bucket).upload(
                path,
                file_bytes,
                {
                    "content-type": content_type,
                    "cacheControl": "3600",  # Cache for 1 hour
                },
            )

            # Return public URL
            return f"{self.supabase_url}/storage/v1/object/public/{bucket}/{path}"
        except Exception as e:
            import logging
            logging.error(f"Avatar upload failed for user {user_id}: {e}")
            return None

    def upload_persona_asset(
        self,
        persona_id: str,
        file_name: str,
        file_bytes: bytes,
        content_type: str = "image/png",
    ) -> Optional[str]:
        """
        Upload persona asset (portrait, background, etc.) and return public URL.

        Args:
            persona_id: Persona ID
            file_name: Filename (e.g., 'portrait.png')
            file_bytes: File bytes
            content_type: MIME type

        Returns:
            Public URL to the asset
        """
        if not self.is_available():
            return None

        try:
            bucket = "persona-assets"
            path = f"personas/{persona_id}/{file_name}"

            self.client.storage.from_(bucket).upload(
                path,
                file_bytes,
                {
                    "content-type": content_type,
                    "cacheControl": "86400",  # Cache for 24 hours
                },
            )

            return f"{self.supabase_url}/storage/v1/object/public/{bucket}/{path}"
        except Exception as e:
            import logging
            logging.error(f"Persona asset upload failed for {persona_id}: {e}")
            return None

    def upload_compiled_config(
        self,
        user_id: str,
        persona_id: str,
        platform: str,
        file_bytes: bytes,
    ) -> Optional[str]:
        """
        Upload compiled persona config (private, signed URL).

        Args:
            user_id: User ID
            persona_id: Persona ID
            platform: Platform (ios, android, web)
            file_bytes: JSON config bytes

        Returns:
            Signed download URL (valid for 1 hour)
        """
        if not self.is_available():
            return None

        try:
            bucket = "compiled-configs"
            path = f"users/{user_id}/{persona_id}/{platform}/config.json"

            # Upload to private bucket
            self.client.storage.from_(bucket).upload(
                path,
                file_bytes,
                {
                    "content-type": "application/json",
                    "cacheControl": "0",  # Don't cache private files
                },
            )

            # Return signed URL valid for 1 hour
            signed_url = self.client.storage.from_(bucket).create_signed_url(path, expires_in=3600)
            return signed_url.get("signedURL") if signed_url else None
        except Exception as e:
            import logging
            logging.error(f"Compiled config upload failed: {e}")
            return None

    def get_download_url(self, bucket: str, path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get signed download URL for a private file.

        Args:
            bucket: Bucket name
            path: File path
            expires_in: Expiration time in seconds

        Returns:
            Signed download URL
        """
        if not self.is_available():
            return None

        try:
            signed_url = self.client.storage.from_(bucket).create_signed_url(path, expires_in)
            return signed_url.get("signedURL") if signed_url else None
        except Exception as e:
            import logging
            logging.error(f"Failed to generate signed URL: {e}")
            return None

    def delete_file(self, bucket: str, path: str) -> bool:
        """
        Delete a file from Supabase Storage.

        Args:
            bucket: Bucket name
            path: File path

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            self.client.storage.from_(bucket).remove([path])
            return True
        except Exception as e:
            import logging
            logging.error(f"Failed to delete file {path}: {e}")
            return False

    def delete_user_files(self, user_id: str) -> bool:
        """
        Delete all files associated with a user (avatar, configs).

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            # Delete avatar
            self.client.storage.from_("user-avatars").remove([f"avatars/{user_id}/"])

            # Delete compiled configs
            self.client.storage.from_("compiled-configs").remove([f"users/{user_id}/"])

            return True
        except Exception as e:
            import logging
            logging.error(f"Failed to delete user files: {e}")
            return False


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get the global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager


def is_storage_available() -> bool:
    """Check if Supabase Storage is configured and available."""
    return get_storage_manager().is_available()
