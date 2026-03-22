from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import ORMModel


class LoginRequest(ORMModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("email must not be empty")
        return cleaned


class UserRead(ORMModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool
    is_admin: bool
    created_at: datetime


class TokenResponse(ORMModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserRead
