from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

MINIMUM_AGE_YEARS = 18


def _age_years(dob: date) -> int:
    today = date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    date_of_birth: date

    @field_validator("date_of_birth")
    @classmethod
    def _reject_underage(cls, value: date) -> date:
        """T2-054 — age verification. Self-reported date of birth, not a
        real ID/age-verification-provider check; that's a separate, more
        invasive integration this repo doesn't attempt."""
        if value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        if _age_years(value) < MINIMUM_AGE_YEARS:
            raise ValueError(f"must be at least {MINIMUM_AGE_YEARS} years old to register")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    email_verified: bool


class PersonaSummary(BaseModel):
    persona_id: str
    name: str
    description: str
    is_historical: bool
    k_layer_available: bool


class PersonaDetail(PersonaSummary):
    model: str
    has_disclosure: bool
    hpep100_blocks: dict[str, str]


class CEIDMeasureRequest(BaseModel):
    conversation: str = Field(min_length=1, max_length=10_000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    content: str
    created_at: datetime


class CheckoutRequest(BaseModel):
    persona_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    test_mode: bool


class ApiKeyCreateResponse(BaseModel):
    """Raw key is returned exactly once, at creation — never again (T2-010)."""
    id: int
    api_key: str
    key_preview: str


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key_preview: str
    created_at: datetime
    revoked: bool


class PurchaseResponse(BaseModel):
    """Minimal order-history record (T2-025). Not a real invoice/receipt PDF —
    that requires Stripe billing/invoicing, which needs a live account the
    user hasn't set up (blocked-business, see T2-021)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    persona_id: str
    stripe_checkout_session_id: str | None
    stripe_payment_status: str
    created_at: datetime


class DataExportResponse(BaseModel):
    """GDPR Art. 20 data-portability export (T2-053)."""
    user: UserResponse
    date_of_birth: date
    purchases: list[PurchaseResponse]
    chat_messages: list[ChatMessageResponse]
    api_keys: list[ApiKeyResponse]
