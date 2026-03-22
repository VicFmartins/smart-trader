from __future__ import annotations

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.models.trade import Trade
from app.repositories.pagination import PagedResult, build_paged_result
from app.schemas.common import PaginationParams
from app.schemas.trade import SortDirection, TradeListParams, TradeResultFilter, TradeSortField


class TradeRepository:
    SORT_FIELD_MAP = {
        TradeSortField.TRADE_DATE: Trade.trade_date,
        TradeSortField.CREATED_AT: Trade.created_at,
        TradeSortField.UPDATED_AT: Trade.updated_at,
        TradeSortField.NET_RESULT: Trade.net_result,
        TradeSortField.GROSS_RESULT: Trade.gross_result,
        TradeSortField.ENTRY_PRICE: Trade.entry_price,
        TradeSortField.EXIT_PRICE: Trade.exit_price,
        TradeSortField.QUANTITY: Trade.quantity,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, trade_id: int) -> Trade | None:
        return self.db.get(Trade, trade_id)

    def create(self, trade: Trade) -> Trade:
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def create_many(self, trades: list[Trade]) -> list[Trade]:
        self.db.add_all(trades)
        self.db.commit()
        for trade in trades:
            self.db.refresh(trade)
        return trades

    def save(self, trade: Trade) -> Trade:
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def delete(self, trade: Trade) -> None:
        self.db.delete(trade)
        self.db.commit()

    def list_trades(
        self,
        *,
        pagination: PaginationParams,
        filters: TradeListParams,
    ) -> PagedResult[Trade]:
        statement = select(Trade)
        count_statement = select(func.count()).select_from(Trade)

        if filters.date_from is not None:
            statement = statement.where(Trade.trade_date >= filters.date_from)
            count_statement = count_statement.where(Trade.trade_date >= filters.date_from)

        if filters.date_to is not None:
            statement = statement.where(Trade.trade_date <= filters.date_to)
            count_statement = count_statement.where(Trade.trade_date <= filters.date_to)

        if filters.asset is not None:
            statement = statement.where(Trade.asset == filters.asset)
            count_statement = count_statement.where(Trade.asset == filters.asset)

        if filters.broker:
            statement = statement.where(Trade.broker == filters.broker)
            count_statement = count_statement.where(Trade.broker == filters.broker)

        if filters.setup_id is not None:
            statement = statement.where(Trade.setup_id == filters.setup_id)
            count_statement = count_statement.where(Trade.setup_id == filters.setup_id)

        if filters.source_type is not None:
            statement = statement.where(Trade.source_type == filters.source_type)
            count_statement = count_statement.where(Trade.source_type == filters.source_type)

        if filters.status is not None:
            statement = statement.where(Trade.status == filters.status)
            count_statement = count_statement.where(Trade.status == filters.status)

        if filters.result_filter == TradeResultFilter.POSITIVE:
            statement = statement.where(Trade.net_result > 0)
            count_statement = count_statement.where(Trade.net_result > 0)
        elif filters.result_filter == TradeResultFilter.NEGATIVE:
            statement = statement.where(Trade.net_result < 0)
            count_statement = count_statement.where(Trade.net_result < 0)

        sort_column = self.SORT_FIELD_MAP[filters.sort_by]
        order_clause = asc(sort_column) if filters.sort_direction == SortDirection.ASC else desc(sort_column)

        items = list(
            self.db.scalars(
                statement.order_by(order_clause, desc(Trade.id))
                .offset(pagination.offset)
                .limit(pagination.limit)
            ).all()
        )
        total = int(self.db.scalar(count_statement) or 0)
        return build_paged_result(items, total, pagination)
