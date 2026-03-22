from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError, TradeValidationError
from app.models.import_job import ImportJob
from app.models.trading_enums import ImportJobStatus, TradeSourceType
from app.repositories.import_jobs import ImportJobRepository
from app.schemas.import_job import ImportJobRead
from app.schemas.pdf_import import PDFImportReviewPayload


class ImportJobService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.import_jobs = ImportJobRepository(db)

    def create_pdf_review_job(self, *, file_name: str) -> ImportJob:
        now = datetime.now(UTC)
        import_job = ImportJob(
            batch_id=self._generate_batch_id(),
            source_type=TradeSourceType.PDF_IMPORT,
            status=ImportJobStatus.PROCESSING,
            file_name=file_name,
            total_trades=0,
            imported_trades=0,
            rejected_trades=0,
            estimated_total_fees=Decimal("0.00"),
            started_at=now,
        )
        return self.import_jobs.create(import_job)

    def complete_pdf_review(
        self,
        *,
        import_job: ImportJob,
        review_payload: PDFImportReviewPayload,
    ) -> ImportJob:
        confidence_scores = [trade.confidence_score for trade in review_payload.trades if trade.confidence_score is not None]
        total_fees = sum(
            ((trade.fees or Decimal("0.00")) for trade in review_payload.trades),
            Decimal("0.00"),
        )

        import_job.status = ImportJobStatus.PENDING
        import_job.broker = review_payload.normalized_broker
        import_job.total_trades = len(review_payload.trades)
        import_job.imported_trades = 0
        import_job.rejected_trades = sum(1 for trade in review_payload.trades if not trade.ready_for_persistence)
        import_job.average_confidence_score = (
            float(
                (sum(Decimal(str(score)) for score in confidence_scores) / Decimal(len(confidence_scores))).quantize(
                    Decimal("0.0001"),
                    rounding=ROUND_HALF_UP,
                )
            )
            if confidence_scores
            else None
        )
        import_job.estimated_total_fees = total_fees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        import_job.error_message = None
        import_job.finished_at = datetime.now(UTC)
        return self.import_jobs.save(import_job)

    def fail_pdf_review(self, *, import_job: ImportJob, message: str) -> ImportJob:
        import_job.status = ImportJobStatus.FAILED
        import_job.error_message = message
        import_job.finished_at = datetime.now(UTC)
        return self.import_jobs.save(import_job)

    def get_import_job(self, *, batch_id: str) -> ImportJob:
        import_job = self.import_jobs.get_by_batch_id(batch_id)
        if import_job is None:
            raise ResourceNotFoundError(f"Import job not found for batch id: {batch_id}")
        return import_job

    def mark_import_confirmed(self, *, batch_id: str, imported_trades: int) -> ImportJob:
        import_job = self.get_import_job(batch_id=batch_id)
        if import_job.source_type != TradeSourceType.PDF_IMPORT:
            raise TradeValidationError("The import batch is not a PDF import job.")
        if import_job.imported_trades > 0:
            raise TradeValidationError("This PDF import batch has already been confirmed.")

        import_job.imported_trades = imported_trades
        import_job.rejected_trades = max(import_job.total_trades - imported_trades, 0)
        import_job.status = ImportJobStatus.COMPLETED if import_job.rejected_trades == 0 else ImportJobStatus.PARTIAL
        import_job.finished_at = datetime.now(UTC)
        return self.import_jobs.save(import_job)

    @staticmethod
    def to_read_model(import_job: ImportJob) -> ImportJobRead:
        return ImportJobRead.model_validate(import_job)

    @staticmethod
    def _generate_batch_id() -> str:
        return f"pdf-{uuid4().hex[:24]}"
