from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class DayTradeTaxMonthBreakdown(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    gross_profit: Decimal = Field(default=Decimal("0.00"), ge=0)
    gross_loss: Decimal = Field(default=Decimal("0.00"), ge=0)
    net_result: Decimal
    prior_loss_carryforward: Decimal = Field(default=Decimal("0.00"), ge=0)
    used_loss_offset: Decimal = Field(default=Decimal("0.00"), ge=0)
    remaining_loss_carryforward: Decimal = Field(default=Decimal("0.00"), ge=0)
    taxable_profit: Decimal = Field(default=Decimal("0.00"), ge=0)
    estimated_tax: Decimal = Field(default=Decimal("0.00"), ge=0)
    darf_code: str = Field(default="6015", min_length=4, max_length=4)


class DayTradeTaxReport(BaseModel):
    tax_rate: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    generated_from: date | None = None
    generated_to: date | None = None
    months: list[DayTradeTaxMonthBreakdown] = Field(default_factory=list)
