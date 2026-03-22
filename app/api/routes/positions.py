from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import pagination_params
from app.db.session import get_db
from app.schemas.common import ListAPIResponse, PaginationParams
from app.schemas.position import PositionRead
from app.services.analytics import PositionQueryService


router = APIRouter()


@router.get("", response_model=ListAPIResponse[PositionRead])
def list_positions(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(pagination_params),
    account_id: Annotated[int | None, Query(ge=1, description="Filter by account id")] = None,
    asset_id: Annotated[int | None, Query(ge=1, description="Filter by asset id")] = None,
    reference_date: Annotated[date | None, Query(description="Filter by reference date (YYYY-MM-DD)")] = None,
) -> ListAPIResponse[PositionRead]:
    result = PositionQueryService(db).list_positions(
        pagination=pagination,
        account_id=account_id,
        asset_id=asset_id,
        reference_date=reference_date,
    )
    return ListAPIResponse(data=result.items, pagination=result.to_pagination_meta())
