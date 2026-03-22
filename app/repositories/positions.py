from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.position_history import PositionHistory
from app.repositories.pagination import PagedResult, build_paged_result
from app.schemas.common import PaginationParams


class PositionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_positions(
        self,
        *,
        pagination: PaginationParams,
        account_id: int | None = None,
        asset_id: int | None = None,
        reference_date: date | None = None,
    ) -> PagedResult[PositionHistory]:
        statement = select(PositionHistory)
        count_statement = select(func.count()).select_from(PositionHistory)

        if account_id is not None:
            statement = statement.where(PositionHistory.account_id == account_id)
            count_statement = count_statement.where(PositionHistory.account_id == account_id)

        if asset_id is not None:
            statement = statement.where(PositionHistory.asset_id == asset_id)
            count_statement = count_statement.where(PositionHistory.asset_id == asset_id)

        if reference_date is not None:
            statement = statement.where(PositionHistory.reference_date == reference_date)
            count_statement = count_statement.where(PositionHistory.reference_date == reference_date)

        items = list(
            self.db.scalars(
                statement.order_by(PositionHistory.reference_date.desc(), PositionHistory.id.desc())
                .offset(pagination.offset)
                .limit(pagination.limit)
            ).all()
        )
        total = int(self.db.scalar(count_statement) or 0)
        return build_paged_result(items, total, pagination)
