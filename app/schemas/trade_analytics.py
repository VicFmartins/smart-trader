from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.models.trading_enums import TradeAsset, TradeSourceType


class TradeAnalyticsFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    asset: TradeAsset | None = None
    broker: str | None = None
    setup_id: int | None = Field(default=None, ge=1)
    source_type: TradeSourceType | None = None

    @field_validator("broker")
    @classmethod
    def normalize_broker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned.upper() if cleaned else None


class TradeAnalyticsSummary(BaseModel):
    total_trades: int = 0
    win_rate: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float | None = None
    expectancy: float = 0.0


class EquityCurvePoint(BaseModel):
    trade_date: date
    daily_net_pnl: float
    equity: float


class DrawdownCurvePoint(BaseModel):
    trade_date: date
    equity: float
    peak_equity: float
    drawdown: float
    drawdown_pct: float


class BreakdownPoint(BaseModel):
    label: str
    pnl: float
    trades: int


class HourBreakdownPoint(BaseModel):
    hour: int = Field(ge=0, le=23)
    pnl: float
    trades: int


class TradeAnalyticsSnapshot(BaseModel):
    summary: TradeAnalyticsSummary
    equity_curve: list[EquityCurvePoint]
    drawdown_curve: list[DrawdownCurvePoint]
    pnl_by_asset: list[BreakdownPoint]
    pnl_by_weekday: list[BreakdownPoint]
    pnl_by_hour: list[HourBreakdownPoint]
    pnl_by_setup: list[BreakdownPoint]
