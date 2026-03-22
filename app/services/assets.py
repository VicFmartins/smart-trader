from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.assets import AssetRepository
from app.repositories.pagination import PagedResult
from app.schemas.common import PaginationParams


class AssetQueryService:
    def __init__(self, db: Session) -> None:
        self.assets = AssetRepository(db)

    def list_assets(
        self,
        *,
        pagination: PaginationParams,
        asset_class: str | None = None,
        ticker: str | None = None,
        search: str | None = None,
    ) -> PagedResult:
        normalized_asset_class = asset_class.strip().lower() if asset_class else None
        normalized_ticker = ticker.strip().upper() if ticker else None
        normalized_search = search.strip() if search else None
        return self.assets.list_assets(
            pagination=pagination,
            asset_class=normalized_asset_class,
            ticker=normalized_ticker,
            search=normalized_search,
        )
