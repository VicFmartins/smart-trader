from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.setup import Setup
from app.models.trade import Trade
from app.models.trading_enums import TradeAsset, TradeSourceType, TradeStatus
from app.schemas.trade_analytics import TradeAnalyticsFilters


@dataclass(frozen=True, slots=True)
class TradeAnalyticsRow:
    trade_id: int
    trade_date: date
    asset: TradeAsset
    broker: str
    setup_id: int | None
    setup_name: str | None
    source_type: TradeSourceType
    created_at: datetime
    trade_time: time | None
    gross_result: Decimal
    net_result: Decimal


class TradeAnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch_rows(self, *, filters: TradeAnalyticsFilters | None = None) -> list[TradeAnalyticsRow]:
        resolved_filters = filters or TradeAnalyticsFilters()
        statement: Select = (
            select(
                Trade.id,
                Trade.trade_date,
                Trade.asset,
                Trade.broker,
                Trade.setup_id,
                Setup.name,
                Trade.source_type,
                Trade.created_at,
                Trade.trade_time,
                Trade.gross_result,
                Trade.net_result,
            )
            .outerjoin(Setup, Trade.setup_id == Setup.id)
            .where(
                Trade.status == TradeStatus.CLOSED,
                Trade.gross_result.is_not(None),
                Trade.net_result.is_not(None),
            )
            .order_by(Trade.trade_date.asc(), Trade.created_at.asc(), Trade.id.asc())
        )

        if resolved_filters.date_from is not None:
            statement = statement.where(Trade.trade_date >= resolved_filters.date_from)
        if resolved_filters.date_to is not None:
            statement = statement.where(Trade.trade_date <= resolved_filters.date_to)
        if resolved_filters.asset is not None:
            statement = statement.where(Trade.asset == resolved_filters.asset)
        if resolved_filters.broker is not None:
            statement = statement.where(Trade.broker == resolved_filters.broker)
        if resolved_filters.setup_id is not None:
            statement = statement.where(Trade.setup_id == resolved_filters.setup_id)
        if resolved_filters.source_type is not None:
            statement = statement.where(Trade.source_type == resolved_filters.source_type)

        rows = self.db.execute(statement).all()
        return [
            TradeAnalyticsRow(
                trade_id=row[0],
                trade_date=row[1],
                asset=row[2],
                broker=row[3],
                setup_id=row[4],
                setup_name=row[5],
                source_type=row[6],
                created_at=row[7],
                trade_time=row[8],
                gross_result=row[9],
                net_result=row[10],
            )
            for row in rows
        ]
