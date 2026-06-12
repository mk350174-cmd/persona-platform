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


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send a password reset link to the user.
    Returns True if sent (or skipped in dev mode), False on error.
    """
    reset_url = f"{BASE_URL}/auth/reset-password?token={reset_token}"

    if not RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping password reset email for %s", to_email)
        logger.info("Dev password reset URL: %s", reset_url)
        return True

    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your Persona Hub password",
            "html": _password_reset_html(reset_url),
            "text": f"Reset your password: {reset_url}\n\nThis link expires in 1 hour.",
        })
        logger.info("Password reset email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", to_email, exc)
        return False


def send_purchase_receipt_email(to_email: str, persona_name: str, amount_usd: float, download_url: str = None) -> bool:
    """
    Send a purchase receipt email to the user.
    Returns True if sent (or skipped in dev mode), False on error.
    """
    if not RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping purchase receipt email for %s", to_email)
        return True

    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"Receipt: {persona_name} persona purchase",
            "html": _purchase_receipt_html(persona_name, amount_usd, download_url),
            "text": f"Thank you for purchasing {persona_name}!\n\nAmount: ${amount_usd:.2f}",
        })
        logger.info("Purchase receipt email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send purchase receipt email to %s: %s", to_email, exc)
        return False


def _verification_html(verify_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0f; color: #e2e8f0; padding: 40px; margin: 0;">
  <div style="max-width: 480px; margin: 0 auto; background: #13131a; border-radius: 12px; padding: 32px; border: 1px solid #2d2d3d;">
    <h1 style="color: #a78bfa; font-size: 24px; margin-bottom: 8px; font-weight: 700;">Verify your email</h1>
    <p style="color: #94a3b8; margin-bottom: 24px; line-height: 1.6;">
      Click the button below to verify your Persona Hub account.
      This link expires in <strong>24 hours</strong>.
    </p>
    <a href="{verify_url}"
       style="display: inline-block; background: #7c3aed; color: white; padding: 12px 28px;
              border-radius: 8px; text-decoration: none; font-weight: 600; text-align: center;">
      Verify Email
    </a>
    <p style="color: #64748b; font-size: 12px; margin-top: 24px; line-height: 1.5;">
      If you didn't create an account, you can safely ignore this email.
    </p>
  </div>
</body>
</html>
""".strip()


def _password_reset_html(reset_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0f; color: #e2e8f0; padding: 40px; margin: 0;">
  <div style="max-width: 480px; margin: 0 auto; background: #13131a; border-radius: 12px; padding: 32px; border: 1px solid #2d2d3d;">
    <h1 style="color: #f87171; font-size: 24px; margin-bottom: 8px; font-weight: 700;">Reset your password</h1>
    <p style="color: #94a3b8; margin-bottom: 24px; line-height: 1.6;">
      Click the button below to set a new password for your account.
      This link expires in <strong>1 hour</strong>.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; background: #f87171; color: white; padding: 12px 28px;
              border-radius: 8px; text-decoration: none; font-weight: 600; text-align: center;">
      Reset Password
    </a>
    <p style="color: #64748b; font-size: 12px; margin-top: 24px; line-height: 1.5;">
      <strong>Didn't request a password reset?</strong> You can safely ignore this email.
      Your password will remain unchanged.
    </p>
  </div>
</body>
</html>
""".strip()


def _purchase_receipt_html(persona_name: str, amount_usd: float, download_url: str = None) -> str:
    download_button = ""
    if download_url:
        download_button = f"""
    <a href="{download_url}"
       style="display: inline-block; background: #22c55e; color: white; padding: 12px 28px;
              border-radius: 8px; text-decoration: none; font-weight: 600; text-align: center; margin-bottom: 24px;">
      Download Config
    </a>
    <p style="color: #94a3b8; margin-bottom: 24px;">Your compiled persona config is ready to download above.</p>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0f; color: #e2e8f0; padding: 40px; margin: 0;">
  <div style="max-width: 480px; margin: 0 auto; background: #13131a; border-radius: 12px; padding: 32px; border: 1px solid #2d2d3d;">
    <h1 style="color: #22c55e; font-size: 24px; margin-bottom: 8px; font-weight: 700;">✓ Purchase confirmed</h1>
    <p style="color: #94a3b8; margin-bottom: 24px; line-height: 1.6;">
      Thank you for purchasing <strong>{persona_name}</strong>!
      You now have full access to this persona.
    </p>
    {download_button}
    <div style="background: #1a1a23; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
      <p style="color: #a78bfa; font-size: 12px; font-weight: 600; margin: 0 0 8px 0;">RECEIPT</p>
      <p style="color: #e2e8f0; margin: 0 0 4px 0; font-size: 16px; font-weight: 600;">{persona_name}</p>
      <p style="color: #94a3b8; margin: 0; font-size: 14px;">${amount_usd:.2f} USD</p>
    </div>
    <p style="color: #64748b; font-size: 12px; line-height: 1.5;">
      You can access your purchases anytime at <strong>persona-hub.com/my-personas</strong>.
      Questions? Contact support@persona-hub.com
    </p>
  </div>
</body>
</html>
""".strip()
