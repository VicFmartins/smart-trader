from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.models.trading_enums import ImportJobStatus, TradeSourceType
from app.schemas.common import ORMModel


class ImportJobBase(ORMModel):
    batch_id: str = Field(min_length=1, max_length=64)
    source_type: TradeSourceType
    status: ImportJobStatus = ImportJobStatus.PENDING
    file_name: str = Field(min_length=1, max_length=255)
    broker: str | None = Field(default=None, max_length=100)
    total_trades: int = Field(default=0, ge=0)
    imported_trades: int = Field(default=0, ge=0)
    rejected_trades: int = Field(default=0, ge=0)
    average_confidence_score: float | None = Field(default=None, ge=0, le=1)
    estimated_total_fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    error_message: str | None = Field(default=None, max_length=4000)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("batch_id", "file_name", "broker", "error_message")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_counts(self) -> "ImportJobBase":
        if self.imported_trades + self.rejected_trades > self.total_trades:
            raise ValueError("Imported plus rejected trades cannot exceed total trades.")
        if self.status == ImportJobStatus.FAILED and not self.error_message:
            raise ValueError("Failed import jobs must include an error message.")
        return self


class ImportJobCreate(ImportJobBase):
    pass


class ImportJobUpdate(ORMModel):
    status: ImportJobStatus | None = None
    broker: str | None = Field(default=None, max_length=100)
    total_trades: int | None = Field(default=None, ge=0)
    imported_trades: int | None = Field(default=None, ge=0)
    rejected_trades: int | None = Field(default=None, ge=0)
    average_confidence_score: float | None = Field(default=None, ge=0, le=1)
    estimated_total_fees: Decimal | None = Field(default=None, ge=0)
    error_message: str | None = Field(default=None, max_length=4000)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("broker", "error_message")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ImportJobRead(ImportJobBase):
    id: int
    created_at: datetime
    updated_at: datetime
