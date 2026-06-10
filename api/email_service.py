"""
Email service — verification emails via Resend API.

Set RESEND_API_KEY env var for production.
If not set and REQUIRE_EMAIL_VERIFICATION=False (default), emails are skipped.
"""

import logging
import os

logger = logging.getLogger("persona_hub.email")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@persona-hub.com")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def send_verification_email(to_email: str, token: str) -> bool:
    """
    Send an email verification link to the user.
    Returns True if sent (or skipped in dev mode), False on error.
    """
    verify_url = f"{BASE_URL}/auth/verify-email?token={token}"

    if not RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping verification email for %s", to_email)
        logger.info("Dev verification URL: %s", verify_url)
        return True

    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Verify your Persona Hub email",
            "html": _verification_html(verify_url),
            "text": f"Verify your email: {verify_url}\n\nThis link expires in 24 hours.",
        })
        logger.info("Verification email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", to_email, exc)
        return False


def _verification_html(verify_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<body style="font-family: Inter, sans-serif; background: #0a0a0f; color: #e2e8f0; padding: 40px;">
  <div style="max-width: 480px; margin: 0 auto; background: #13131a; border-radius: 12px; padding: 32px;">
    <h1 style="color: #a78bfa; font-size: 24px; margin-bottom: 8px;">Verify your email</h1>
    <p style="color: #94a3b8; margin-bottom: 24px;">
      Click the button below to verify your Persona Hub account.
      This link expires in <strong>24 hours</strong>.
    </p>
    <a href="{verify_url}"
       style="display: inline-block; background: #7c3aed; color: white; padding: 12px 28px;
              border-radius: 8px; text-decoration: none; font-weight: 600;">
      Verify Email
    </a>
    <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
      If you didn't create an account, you can safely ignore this email.
    </p>
  </div>
</body>
</html>
""".strip()
