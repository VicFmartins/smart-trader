from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.models.trading_enums import AssetClass
from app.schemas.common import ORMModel


class TaxSummarySnapshotBase(ORMModel):
    competence_month: date
    asset_class: AssetClass | None = None
    broker: str | None = Field(default=None, max_length=100)
    trade_count: int = Field(default=0, ge=0)
    gross_result: Decimal
    total_fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    net_result: Decimal
    taxable_result: Decimal
    irrf_withheld: Decimal = Field(default=Decimal("0.00"), ge=0)
    carried_loss_balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.2000"), ge=0, le=1)
    estimated_tax_due: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("broker", "notes")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("competence_month")
    @classmethod
    def validate_competence_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Competence month must be stored as the first day of the month.")
        return value


class TaxSummarySnapshotCreate(TaxSummarySnapshotBase):
    pass


class TaxSummarySnapshotRead(TaxSummarySnapshotBase):
    id: int
    generated_at: datetime
