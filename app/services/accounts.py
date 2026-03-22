from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.accounts import AccountRepository
from app.repositories.pagination import PagedResult
from app.schemas.common import PaginationParams


class AccountQueryService:
    def __init__(self, db: Session) -> None:
        self.accounts = AccountRepository(db)

    def list_accounts(
        self,
        *,
        pagination: PaginationParams,
        client_id: int | None = None,
        broker: str | None = None,
    ) -> PagedResult:
        normalized_broker = broker.strip().upper() if broker else None
        return self.accounts.list_accounts(
            pagination=pagination,
            client_id=client_id,
            broker=normalized_broker,
        )
