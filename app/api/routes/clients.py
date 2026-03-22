from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import pagination_params
from app.db.session import get_db
from app.schemas.client import ClientRead
from app.schemas.common import ListAPIResponse, PaginationParams
from app.services.clients import ClientQueryService


router = APIRouter()


@router.get("", response_model=ListAPIResponse[ClientRead])
def list_clients(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(pagination_params),
    name: Annotated[str | None, Query(description="Filter by partial client name")] = None,
    risk_profile: Annotated[str | None, Query(description="Filter by risk profile")] = None,
) -> ListAPIResponse[ClientRead]:
    result = ClientQueryService(db).list_clients(pagination=pagination, name=name, risk_profile=risk_profile)
    return ListAPIResponse(data=result.items, pagination=result.to_pagination_meta())
