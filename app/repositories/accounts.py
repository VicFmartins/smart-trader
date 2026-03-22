from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.repositories.pagination import PagedResult, build_paged_result
from app.schemas.common import PaginationParams


class AccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_accounts(
        self,
        *,
        pagination: PaginationParams,
        client_id: int | None = None,
        broker: str | None = None,
    ) -> PagedResult[Account]:
        statement = select(Account)
        count_statement = select(func.count()).select_from(Account)

        if client_id is not None:
            statement = statement.where(Account.client_id == client_id)
            count_statement = count_statement.where(Account.client_id == client_id)

        if broker:
            statement = statement.where(Account.broker == broker)
            count_statement = count_statement.where(Account.broker == broker)

        items = list(
            self.db.scalars(
                statement.order_by(Account.id).offset(pagination.offset).limit(pagination.limit)
            ).all()
        )
        total = int(self.db.scalar(count_statement) or 0)
        return build_paged_result(items, total, pagination)
