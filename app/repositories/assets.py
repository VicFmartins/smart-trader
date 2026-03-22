from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.asset_master import AssetMaster
from app.repositories.pagination import PagedResult, build_paged_result
from app.schemas.common import PaginationParams


class AssetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_assets(
        self,
        *,
        pagination: PaginationParams,
        asset_class: str | None = None,
        ticker: str | None = None,
        search: str | None = None,
    ) -> PagedResult[AssetMaster]:
        statement = select(AssetMaster)
        count_statement = select(func.count()).select_from(AssetMaster)

        if asset_class:
            statement = statement.where(AssetMaster.asset_class == asset_class)
            count_statement = count_statement.where(AssetMaster.asset_class == asset_class)

        if ticker:
            statement = statement.where(AssetMaster.ticker == ticker)
            count_statement = count_statement.where(AssetMaster.ticker == ticker)

        if search:
            pattern = f"%{search}%"
            search_clause = or_(
                AssetMaster.normalized_name.ilike(pattern),
                AssetMaster.original_name.ilike(pattern),
                AssetMaster.ticker.ilike(pattern),
            )
            statement = statement.where(search_clause)
            count_statement = count_statement.where(search_clause)

        items = list(
            self.db.scalars(
                statement.order_by(AssetMaster.normalized_name)
                .offset(pagination.offset)
                .limit(pagination.limit)
            ).all()
        )
        total = int(self.db.scalar(count_statement) or 0)
        return build_paged_result(items, total, pagination)
