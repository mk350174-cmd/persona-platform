from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


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


class CheckoutRequest(BaseModel):
    persona_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    test_mode: bool
