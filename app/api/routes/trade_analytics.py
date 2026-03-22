from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.trading_enums import TradeAsset
from app.schemas.common import APIResponse
from app.schemas.trade_analytics import TradeAnalyticsFilters, TradeAnalyticsSnapshot
from app.services.trade_analytics import TradeAnalyticsService


router = APIRouter(prefix="/analytics/trades")


@router.get("", response_model=APIResponse[TradeAnalyticsSnapshot])
def get_trade_analytics_snapshot(
    db: Session = Depends(get_db),
    date_from: Annotated[date | None, Query(description="Filter trades from this date (inclusive)")] = None,
    date_to: Annotated[date | None, Query(description="Filter trades until this date (inclusive)")] = None,
    asset: Annotated[TradeAsset | None, Query(description="Filter by asset code")] = None,
    broker: Annotated[str | None, Query(description="Filter by broker")] = None,
    setup_id: Annotated[int | None, Query(ge=1, description="Filter by setup id")] = None,
) -> APIResponse[TradeAnalyticsSnapshot]:
    filters = TradeAnalyticsFilters(
        date_from=date_from,
        date_to=date_to,
        asset=asset,
        broker=broker,
        setup_id=setup_id,
    )
    snapshot = TradeAnalyticsService(db).build_snapshot(filters=filters)
    return APIResponse(data=snapshot)
