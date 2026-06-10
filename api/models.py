"""Request and response models with input validation and output filtering."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ── Request Models (Input Validation with extra='forbid') ───────────────────────

class RegisterRequest(BaseModel):
    """User registration request."""

    model_config = ConfigDict(extra='forbid')  # Reject unknown fields
    email: str = Field(..., description="Your email address")


class CompileRequest(BaseModel):
    """Persona compilation request."""

    model_config = ConfigDict(extra='forbid')
    platform: str = Field(default="gemini", description="gemini | claude | openai | raw")
    tier: str = Field(default="standard", description="nano | standard | rich")


class AllPlatformsRequest(BaseModel):
    """Multi-platform compilation request."""

    model_config = ConfigDict(extra='forbid')
    tier: str = Field(default="standard")


class AllTiersRequest(BaseModel):
    """Multi-tier compilation request."""

    model_config = ConfigDict(extra='forbid')
    platform: str = Field(default="gemini")


class VoiceRequest(BaseModel):
    """Voice synthesis request."""

    model_config = ConfigDict(extra='forbid')
    text: str = Field(
        ...,
        description="Text to synthesize as speech",
        min_length=1,
        max_length=2000,
    )


class SubscribeRequest(BaseModel):
    """Subscription request."""

    model_config = ConfigDict(extra='forbid')
    tier: str = Field(..., description="basic | pro | enterprise")


# ── Response Models (Output Filtering - No Sensitive Fields) ───────────────────

class UserResponse(BaseModel):
    """User profile response (filtered fields only)."""

    model_config = ConfigDict(extra='forbid')
    id: int
    email: str
    created_at: datetime
    subscription_tier: str
    # NOTE: Never expose api_key, password_hash, internal_notes, etc.


class PersonaBasicResponse(BaseModel):
    """Persona basic info response."""

    model_config = ConfigDict(extra='forbid')
    id: str
    name: str
    description: Optional[str]
    domain: Optional[str]
    price_usd: float
    image_url: Optional[str]
    # NOTE: Never expose internal K-layer, CEID scores marked as internal, etc.


class PersonaDetailResponse(PersonaBasicResponse):
    """Persona detailed response with optional scores."""

    model_config = ConfigDict(extra='forbid')
    tags: Optional[list[str]]
    system_instruction_preview: Optional[str]
    ceid_score: Optional[float]  # Only if requested
    metallic_score: Optional[float]  # Only if requested
    quadrant: Optional[str]  # Only if requested
    power_ethics_ratio: Optional[float]  # Only if requested


class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(extra='forbid')
    status: str  # "ok" or "degraded"
    version: str
    db: bool
    personas: int


class CheckoutResponse(BaseModel):
    """Checkout session response."""

    model_config = ConfigDict(extra='forbid')
    session_id: str
    url: str
    # NOTE: Never expose Stripe secret keys, payment method details, etc.


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    model_config = ConfigDict(extra='forbid')
    tier: str
    status: str
    renewal_date: Optional[datetime]
    request_limit: Optional[int]
    request_used: Optional[int]


class PurchaseListResponse(BaseModel):
    """Purchase list response."""

    model_config = ConfigDict(extra='forbid')
    total: int
    page: list[dict]  # Safe persona preview


class CatalogResponse(BaseModel):
    """Catalog listing response."""

    model_config = ConfigDict(extra='forbid')
    total: int
    page: list[PersonaDetailResponse]
