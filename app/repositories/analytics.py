from __future__ import annotations

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.asset_master import AssetMaster
from app.models.client import Client
from app.models.ingestion_report import IngestionReport
from app.models.position_history import PositionHistory


class AnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch_portfolio_rows(
        self,
        *,
        client_name: str | None = None,
        asset_class: str | None = None,
    ) -> list[tuple]:
        statement: Select = (
            select(
                Client.name,
                Client.risk_profile,
                Account.broker,
                AssetMaster.asset_class,
                AssetMaster.ticker,
                AssetMaster.normalized_name,
                PositionHistory.quantity,
                PositionHistory.avg_price,
                PositionHistory.total_value,
                PositionHistory.reference_date,
            )
            .join(Account, PositionHistory.account_id == Account.id)
            .join(Client, Account.client_id == Client.id)
            .join(AssetMaster, PositionHistory.asset_id == AssetMaster.id)
            .order_by(desc(PositionHistory.reference_date), desc(PositionHistory.total_value))
        )

        if client_name:
            statement = statement.where(Client.name == client_name)
        if asset_class:
            statement = statement.where(AssetMaster.asset_class == asset_class)

        return list(self.db.execute(statement).all())

    def count_pending_reviews(self) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(IngestionReport).where(
                    IngestionReport.review_required.is_(True),
                    IngestionReport.review_status == "pending",
                    IngestionReport.status == "review_required",
                )
            )
            or 0
        )
