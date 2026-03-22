from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trade import Trade
from app.models.trading_enums import TradeStatus


@dataclass(frozen=True, slots=True)
class DayTradeTaxRow:
    trade_date: date
    net_result: Decimal


class DayTradeTaxRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch_rows(self) -> list[DayTradeTaxRow]:
        statement = (
            select(Trade.trade_date, Trade.net_result)
            .where(
                Trade.status == TradeStatus.CLOSED,
                Trade.net_result.is_not(None),
            )
            .order_by(Trade.trade_date.asc(), Trade.created_at.asc(), Trade.id.asc())
        )
        rows = self.db.execute(statement).all()
        return [DayTradeTaxRow(trade_date=row[0], net_result=row[1]) for row in rows]
