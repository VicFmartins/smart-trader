from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.ingestion_report import IngestionReport
from app.repositories.pagination import PagedResult, build_paged_result
from app.schemas.common import PaginationParams


class IngestionReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, report: IngestionReport) -> IngestionReport:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def save(self, report: IngestionReport) -> IngestionReport:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def rollback(self) -> None:
        self.db.rollback()

    def get_by_id(self, report_id: int) -> IngestionReport:
        report = self.db.get(IngestionReport, report_id)
        if report is None:
            raise ResourceNotFoundError(f"Ingestion report not found: {report_id}")
        return report

    def list_reports(
        self,
        *,
        pagination: PaginationParams,
        review_required: bool | None = None,
        review_status: str | None = None,
    ) -> PagedResult[IngestionReport]:
        statement = select(IngestionReport)
        count_statement = select(func.count()).select_from(IngestionReport)

        if review_required is not None:
            statement = statement.where(IngestionReport.review_required == review_required)
            count_statement = count_statement.where(IngestionReport.review_required == review_required)
        if review_status:
            statement = statement.where(IngestionReport.review_status == review_status)
            count_statement = count_statement.where(IngestionReport.review_status == review_status)

        items = list(
            self.db.scalars(
                statement.order_by(IngestionReport.created_at.desc(), IngestionReport.id.desc())
                .offset(pagination.offset)
                .limit(pagination.limit)
            ).all()
        )
        total = int(self.db.scalar(count_statement) or 0)
        return build_paged_result(items, total, pagination)
