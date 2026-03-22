from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import pagination_params
from app.db.session import get_db
from app.models.trading_enums import TradeAsset, TradeSourceType, TradeStatus
from app.schemas.common import APIResponse, ListAPIResponse, PaginationParams
from app.schemas.trade import (
    SortDirection,
    TradeBulkCreate,
    TradeBulkCreateResponse,
    TradeCreate,
    TradeDeleteResponse,
    TradeListParams,
    TradeRead,
    TradeResultFilter,
    TradeSortField,
    TradeUpdate,
)
from app.services.trades import TradeService


router = APIRouter(prefix="/trades")


@router.post("", response_model=APIResponse[TradeRead])
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)) -> APIResponse[TradeRead]:
    trade = TradeService(db).create_trade(payload)
    return APIResponse(data=trade)


@router.post("/bulk", response_model=APIResponse[TradeBulkCreateResponse])
def create_trades_bulk(payload: TradeBulkCreate, db: Session = Depends(get_db)) -> APIResponse[TradeBulkCreateResponse]:
    trades, import_batch_id = TradeService(db).create_trades_bulk(payload.trades)
    return APIResponse(
        data=TradeBulkCreateResponse(
            created_count=len(trades),
            import_batch_id=import_batch_id,
            trades=[TradeRead.model_validate(trade) for trade in trades],
        )
    )


@router.get("", response_model=ListAPIResponse[TradeRead])
def list_trades(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(pagination_params),
    date_from: Annotated[date | None, Query(description="Filter trades from this date (inclusive)")] = None,
    date_to: Annotated[date | None, Query(description="Filter trades until this date (inclusive)")] = None,
    asset: Annotated[TradeAsset | None, Query(description="Filter by asset code")] = None,
    broker: Annotated[str | None, Query(description="Filter by broker")] = None,
    setup_id: Annotated[int | None, Query(ge=1, description="Filter by setup id")] = None,
    source_type: Annotated[TradeSourceType | None, Query(description="Filter by source type")] = None,
    status: Annotated[TradeStatus | None, Query(description="Filter by trade status")] = None,
    result_filter: Annotated[TradeResultFilter | None, Query(description="Filter by positive or negative result")] = None,
    sort_by: Annotated[TradeSortField, Query(description="Field used for sorting")] = TradeSortField.TRADE_DATE,
    sort_direction: Annotated[SortDirection, Query(description="Sorting direction")] = SortDirection.DESC,
) -> ListAPIResponse[TradeRead]:
    filters = TradeListParams(
        date_from=date_from,
        date_to=date_to,
        asset=asset,
        broker=broker,
        setup_id=setup_id,
        source_type=source_type,
        status=status,
        result_filter=result_filter,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    result = TradeService(db).list_trades(pagination=pagination, filters=filters)
    return ListAPIResponse(data=result.items, pagination=result.to_pagination_meta())


@router.get("/{trade_id}", response_model=APIResponse[TradeRead])
def get_trade(trade_id: int, db: Session = Depends(get_db)) -> APIResponse[TradeRead]:
    trade = TradeService(db).get_trade(trade_id)
    return APIResponse(data=trade)


@router.patch("/{trade_id}", response_model=APIResponse[TradeRead])
def update_trade(trade_id: int, payload: TradeUpdate, db: Session = Depends(get_db)) -> APIResponse[TradeRead]:
    trade = TradeService(db).update_trade(trade_id, payload)
    return APIResponse(data=trade)


@router.delete("/{trade_id}", response_model=APIResponse[TradeDeleteResponse])
def delete_trade(trade_id: int, db: Session = Depends(get_db)) -> APIResponse[TradeDeleteResponse]:
    TradeService(db).delete_trade(trade_id)
    return APIResponse(data=TradeDeleteResponse(trade_id=trade_id))
