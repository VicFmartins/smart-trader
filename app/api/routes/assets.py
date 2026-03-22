from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import pagination_params
from app.db.session import get_db
from app.schemas.asset import AssetRead
from app.schemas.common import ListAPIResponse, PaginationParams
from app.services.assets import AssetQueryService


router = APIRouter()


@router.get("", response_model=ListAPIResponse[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(pagination_params),
    asset_class: Annotated[str | None, Query(description="Filter by asset class")] = None,
    ticker: Annotated[str | None, Query(description="Filter by exact ticker")] = None,
    search: Annotated[str | None, Query(description="Search by asset name or ticker")] = None,
) -> ListAPIResponse[AssetRead]:
    result = AssetQueryService(db).list_assets(
        pagination=pagination,
        asset_class=asset_class,
        ticker=ticker,
        search=search,
    )
    return ListAPIResponse(data=result.items, pagination=result.to_pagination_meta())
