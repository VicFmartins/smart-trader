from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import ETLInputError
from app.etl.contracts import ETLFileSummary
from app.etl.detect.column_mapper import build_layout_signature
from app.models.ingestion_report import IngestionReport
from app.repositories.ingestion_reports import IngestionReportRepository
from app.repositories.pagination import PagedResult
from app.schemas.common import PaginationParams
from app.services.accepted_mapping_service import AcceptedMappingService


@dataclass(frozen=True, slots=True)
class IngestionReportPayload:
    filename: str
    source_file: str
    source_type: str
    detected_type: str
    layout_signature: str | None
    raw_file: str | None
    processed_file: str | None
    parser_name: str | None
    detection_confidence: float | None
    review_required: bool
    review_status: str
    review_reasons: list[str]
    detected_columns: list[str]
    applied_mappings: list[dict[str, object]]
    structure_detection: dict[str, object]
    rows_processed: int
    rows_skipped: int
    status: str
    message: str
    processed_at: datetime | None


class IngestionReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reports = IngestionReportRepository(db)

    def create_report(self, payload: IngestionReportPayload) -> IngestionReport:
        report = IngestionReport(
            filename=payload.filename,
            source_file=payload.source_file,
            source_type=payload.source_type,
            detected_type=payload.detected_type,
            layout_signature=payload.layout_signature,
            raw_file=payload.raw_file,
            processed_file=payload.processed_file,
            parser_name=payload.parser_name,
            detection_confidence=payload.detection_confidence,
            review_required=payload.review_required,
            review_status=payload.review_status,
            review_reasons=payload.review_reasons,
            detected_columns=payload.detected_columns,
            applied_mappings=payload.applied_mappings,
            structure_detection=payload.structure_detection,
            rows_processed=payload.rows_processed,
            rows_skipped=payload.rows_skipped,
            status=payload.status,
            message=payload.message,
            processed_at=payload.processed_at,
        )
        return self.reports.add(report)

    def create_success_report(
        self,
        *,
        summary: ETLFileSummary,
        filename: str,
        source_type: str,
        detected_type: str,
        message: str,
    ) -> IngestionReport:
        return self.create_report(
            IngestionReportPayload(
                filename=filename,
                source_file=summary.source_file,
                source_type=source_type,
                detected_type=detected_type,
                layout_signature=summary.layout_signature or build_layout_signature(summary.detected_columns),
                raw_file=str(summary.raw_file),
                processed_file=str(summary.processed_file),
                parser_name=summary.parser_name,
                detection_confidence=summary.detection_confidence,
                review_required=summary.review_required,
                review_status="pending" if summary.review_required else "not_required",
                review_reasons=list(summary.review_reasons),
                detected_columns=list(summary.detected_columns),
                applied_mappings=list(summary.applied_mappings),
                structure_detection=summary.structure_detection or {},
                rows_processed=summary.rows_processed,
                rows_skipped=summary.rows_skipped,
                status="review_required" if summary.review_required else "success",
                message=message,
                processed_at=datetime.now(UTC),
            )
        )

    def create_failure_report(
        self,
        *,
        filename: str,
        source_file: str,
        source_type: str,
        detected_type: str,
        message: str,
    ) -> IngestionReport:
        self.reports.rollback()
        return self.create_report(
            IngestionReportPayload(
                filename=filename,
                source_file=source_file,
                source_type=source_type,
                detected_type=detected_type,
                layout_signature=None,
                raw_file=None,
                processed_file=None,
                parser_name=None,
                detection_confidence=None,
                review_required=True,
                review_status="pending",
                review_reasons=["processing_failed"],
                detected_columns=[],
                applied_mappings=[],
                structure_detection={},
                rows_processed=0,
                rows_skipped=0,
                status="error",
                message=message,
                processed_at=datetime.now(UTC),
            )
        )

    def update_report_from_summary(
        self,
        report: IngestionReport,
        *,
        summary: ETLFileSummary,
        filename: str,
        source_type: str,
        detected_type: str,
        message: str,
    ) -> IngestionReport:
        report.filename = filename
        report.source_file = summary.source_file
        report.source_type = source_type
        report.detected_type = detected_type
        report.layout_signature = summary.layout_signature or build_layout_signature(summary.detected_columns)
        report.raw_file = str(summary.raw_file)
        report.processed_file = str(summary.processed_file)
        report.parser_name = summary.parser_name
        report.detection_confidence = summary.detection_confidence
        report.review_required = summary.review_required
        report.review_status = "pending" if summary.review_required else "not_required"
        report.review_reasons = list(summary.review_reasons)
        report.detected_columns = list(summary.detected_columns)
        report.applied_mappings = list(summary.applied_mappings)
        report.structure_detection = summary.structure_detection or {}
        report.rows_processed = summary.rows_processed
        report.rows_skipped = summary.rows_skipped
        report.status = "review_required" if summary.review_required else "success"
        report.message = message
        report.processed_at = datetime.now(UTC)
        report.reprocessed_at = datetime.now(UTC)
        report.reprocess_count += 1
        return self.reports.save(report)

    def mark_reprocess_failure(self, report: IngestionReport, *, message: str) -> IngestionReport:
        self.reports.rollback()
        persistent_report = self.get_report(report.id)
        persistent_report.status = "error"
        persistent_report.message = message
        persistent_report.review_required = True
        persistent_report.review_status = "pending"
        persistent_report.review_reasons = ["reprocess_failed"]
        persistent_report.processed_at = datetime.now(UTC)
        persistent_report.reprocessed_at = datetime.now(UTC)
        persistent_report.reprocess_count += 1
        return self.reports.save(persistent_report)

    def list_reports(
        self,
        *,
        pagination: PaginationParams,
        review_required: bool | None = None,
        review_status: str | None = None,
    ) -> PagedResult:
        normalized_status = review_status.strip().lower() if review_status else None
        return self.reports.list_reports(
            pagination=pagination,
            review_required=review_required,
            review_status=normalized_status,
        )

    def get_report(self, report_id: int) -> IngestionReport:
        return self.reports.get_by_id(report_id)

    def update_review_status(
        self,
        report_id: int,
        *,
        review_status: str,
        approved_by: str | None = None,
    ) -> IngestionReport:
        report = self.get_report(report_id)
        normalized_status = review_status.strip().lower()
        if report.status == "error" and normalized_status == "approved":
            raise ETLInputError(
                "Technical ingestion failures cannot be approved. Fix the source file and upload it again, or "
                "reprocess only successful review-required runs."
            )
        report.review_status = normalized_status
        report.review_required = normalized_status == "pending"
        if normalized_status == "approved":
            report.review_required = False
            AcceptedMappingService(self.db).persist_from_report(report, approved_by=approved_by)
        elif normalized_status in {"rejected", "not_required"}:
            report.review_required = False
        return self.reports.save(report)


def detect_ingestion_type(source_reference: str | Path) -> str:
    suffix = Path(str(source_reference)).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".xlsx", ".xls"}:
        return "excel"
    if suffix == ".json":
        return "json"
    if Path(str(source_reference)).is_dir():
        return "directory"
    return suffix.lstrip(".") or "unknown"
