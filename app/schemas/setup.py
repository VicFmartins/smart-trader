from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.models.trading_enums import AssetClass
from app.schemas.common import ORMModel


class SetupBase(ORMModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    asset_class_scope: AssetClass | None = None
    is_active: bool = True

    @field_validator("name", "description")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SetupCreate(SetupBase):
    pass


class SetupUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    asset_class_scope: AssetClass | None = None
    is_active: bool | None = None

    @field_validator("name", "description")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SetupRead(SetupBase):
    id: int
    created_at: datetime
    updated_at: datetime
