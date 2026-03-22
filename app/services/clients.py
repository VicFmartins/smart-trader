from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.clients import ClientRepository
from app.repositories.pagination import PagedResult
from app.schemas.common import PaginationParams


class ClientQueryService:
    def __init__(self, db: Session) -> None:
        self.clients = ClientRepository(db)

    def list_clients(
        self,
        *,
        pagination: PaginationParams,
        name: str | None = None,
        risk_profile: str | None = None,
    ) -> PagedResult:
        normalized_name = name.strip() if name else None
        normalized_risk_profile = risk_profile.strip().lower() if risk_profile else None
        return self.clients.list_clients(
            pagination=pagination,
            name=normalized_name,
            risk_profile=normalized_risk_profile,
        )
