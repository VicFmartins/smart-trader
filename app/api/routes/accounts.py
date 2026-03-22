from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import pagination_params
from app.db.session import get_db
from app.schemas.account import AccountRead
from app.schemas.common import ListAPIResponse, PaginationParams
from app.services.accounts import AccountQueryService


router = APIRouter()


@router.get("", response_model=ListAPIResponse[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(pagination_params),
    client_id: Annotated[int | None, Query(ge=1, description="Filter by client id")] = None,
    broker: Annotated[str | None, Query(description="Filter by broker name")] = None,
) -> ListAPIResponse[AccountRead]:
    result = AccountQueryService(db).list_accounts(pagination=pagination, client_id=client_id, broker=broker)
    return ListAPIResponse(data=result.items, pagination=result.to_pagination_meta())
