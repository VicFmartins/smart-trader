from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Iterable
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ApplicationError, ETLInputError, ResourceNotFoundError
from app.db.session import session_scope
from app.etl.extract.file_reader import discover_input_files
from app.etl.pipeline import PortfolioETLPipeline
from app.lambda_handlers.event_parser import LambdaInvocation, S3EventObject
from app.models.ingestion_report import IngestionReport
from app.schemas.etl import ETLFileResult, ETLRunResponse, UploadResponse
from app.services.alert_service import AlertService
from app.services.ingestion_reports import IngestionReportService, detect_ingestion_type


logger = logging.getLogger(__name__)


class ImportPipelineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.pipeline = PortfolioETLPipeline(db)
        self.ingestion_reports = IngestionReportService(db)
        self.alerts = AlertService()

    def run(self, source_path: str | None = None, *, source_type: str = "local") -> ETLRunResponse:
        files = self._resolve_local_files(source_path)
        results = [
            self._run_with_report(
                source_type=source_type,
                source_path=file_path,
                filename=file_path.name,
                detected_type=detect_ingestion_type(file_path),
            )
            for file_path in files
        ]
        return self._build_response(results)

    def run_from_s3(self, *, s3_key: str | None = None, s3_prefix: str | None = None) -> ETLRunResponse:
        source_reference = s3_key or s3_prefix or "s3"
        result = self._run_with_report(
            source_type="s3",
            s3_key=s3_key,
            s3_prefix=s3_prefix,
            filename=Path(source_reference).name or "s3_ingestion",
            detected_type=detect_ingestion_type(source_reference),
        )
        return self._build_response([result])

    def run_many_from_s3(self, s3_keys: Iterable[str]) -> ETLRunResponse:
        results = [
            self._run_with_report(
                source_type="s3",
                s3_key=s3_key,
                filename=Path(s3_key).name or "s3_ingestion",
                detected_type=detect_ingestion_type(s3_key),
            )
            for s3_key in s3_keys
        ]
        return self._build_response(results)

    def process_s3_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
        source_type: str = "lambda_s3",
    ) -> tuple:
        filename = Path(object_key).name or "s3_ingestion"
        return self._run_with_report(
            source_type="s3",
            report_source_type=source_type,
            s3_bucket_name=bucket_name,
            s3_key=object_key,
            filename=filename,
            detected_type=detect_ingestion_type(object_key),
        )

    def run_many_s3_objects(
        self,
        s3_objects: Iterable[S3EventObject],
        *,
        source_type: str = "lambda_s3",
    ) -> ETLRunResponse:
        results = [
            self.process_s3_object(
                bucket_name=s3_object.bucket_name,
                object_key=s3_object.object_key,
                source_type=source_type,
            )
            for s3_object in s3_objects
        ]
        return self._build_response(results)

    def run_from_lambda_invocation(self, invocation: LambdaInvocation) -> ETLRunResponse:
        if invocation.invocation_type == "s3_event":
            return self.run_many_s3_objects(invocation.s3_objects, source_type="lambda_s3")
        if invocation.invocation_type == "direct_s3":
            return self.run_from_s3(s3_key=invocation.s3_key, s3_prefix=invocation.s3_prefix)
        return self.run(source_path=invocation.source_path)

    def save_uploaded_file(self, filename: str, file_stream: BinaryIO) -> Path:
        cleaned_name = Path(filename or "").name
        if not cleaned_name:
            raise ETLInputError("Uploaded file must include a valid filename.")

        suffix = Path(cleaned_name).suffix.lower()
        if suffix not in self.settings.supported_extensions:
            supported = ", ".join(self.settings.supported_extensions)
            raise ETLInputError(f"Unsupported uploaded file type '{suffix}'. Supported types: {supported}.")

        upload_dir = self.settings.raw_data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = "".join(character if character.isalnum() else "_" for character in Path(cleaned_name).stem).strip("_")
        safe_stem = (safe_stem or "file")[:48]
        destination = upload_dir / f"upload_{uuid4().hex}_{safe_stem}{suffix}"
        file_stream.seek(0)
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file_stream, buffer)

        logger.info("Saved uploaded file %s to temporary work path %s", cleaned_name, destination)
        return destination

    def process_uploaded_file(self, file_path: str | Path, *, original_filename: str | None = None) -> UploadResponse:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise ResourceNotFoundError(f"Uploaded working file not found: {path}")

        suffix = path.suffix.lower()
        if suffix not in self.settings.supported_extensions:
            supported = ", ".join(self.settings.supported_extensions)
            raise ETLInputError(f"Unsupported uploaded file type '{suffix}'. Supported types: {supported}.")

        filename = original_filename or path.name
        detected_type = self._detect_uploaded_type(path)
        summary, report = self._run_with_report(
            source_type="local",
            source_path=path,
            filename=filename,
            detected_type=detected_type,
        )
        message = f"Arquivo {filename} processado com sucesso."
        return UploadResponse(
            ingestion_report_id=report.id,
            filename=filename,
            detected_type=detected_type,
            rows_processed=summary.rows_processed,
            rows_skipped=summary.rows_skipped,
            message=message,
            processed_at=datetime.now(UTC).isoformat(),
            raw_file=str(summary.raw_file),
            processed_file=str(summary.processed_file),
            detection_confidence=summary.detection_confidence,
            review_required=summary.review_required,
            review_status=report.review_status,
            review_reasons=list(summary.review_reasons),
            reprocessed_at=report.reprocessed_at.isoformat() if report.reprocessed_at else None,
            reprocess_count=report.reprocess_count,
        )

    def reprocess_report(self, report_id: int) -> UploadResponse:
        report = self.ingestion_reports.get_report(report_id)
        if report.status == "error":
            raise ETLInputError(
                "Technical ingestion failures cannot be reprocessed in place. Upload a corrected file to create a new run."
            )
        if report.review_status not in {"approved", "not_required"}:
            raise ETLInputError("Only approved or not-required ingestion reports can be reprocessed.")

        source_type, source_path, s3_key = self._resolve_reprocess_source(report)
        filename = report.filename

        try:
            summary = self.pipeline.run(source_path, source_type=source_type, s3_key=s3_key)
            message = f"Arquivo {filename} reprocessado com sucesso."
            updated_report = self.ingestion_reports.update_report_from_summary(
                report,
                summary=summary,
                filename=filename,
                source_type=source_type,
                detected_type=detect_ingestion_type(summary.source_file),
                message=message,
            )
            self.alerts.notify_ingestion_report(updated_report)
            return UploadResponse(
                ingestion_report_id=updated_report.id,
                filename=filename,
                detected_type=updated_report.detected_type,
                rows_processed=summary.rows_processed,
                rows_skipped=summary.rows_skipped,
                message=updated_report.message,
                processed_at=updated_report.processed_at.isoformat() if updated_report.processed_at else datetime.now(UTC).isoformat(),
                raw_file=str(updated_report.raw_file or ""),
                processed_file=str(updated_report.processed_file or ""),
                detection_confidence=summary.detection_confidence,
                review_required=updated_report.review_required,
                review_status=updated_report.review_status,
                review_reasons=list(updated_report.review_reasons or []),
                reprocessed_at=updated_report.reprocessed_at.isoformat() if updated_report.reprocessed_at else None,
                reprocess_count=updated_report.reprocess_count,
            )
        except ApplicationError as exc:
            failed_report = self.ingestion_reports.mark_reprocess_failure(report, message=exc.message)
            self.alerts.notify_ingestion_report(failed_report)
            raise
        except Exception as exc:
            failed_report = self.ingestion_reports.mark_reprocess_failure(report, message=str(exc) or "Unexpected reprocessing failure.")
            self.alerts.notify_ingestion_report(failed_report)
            raise

    @classmethod
    def process_uploaded_stream(cls, filename: str, file_stream: BinaryIO) -> UploadResponse:
        with session_scope() as db:
            service = cls(db)
            temp_path = service.save_uploaded_file(filename, file_stream)
            try:
                return service.process_uploaded_file(temp_path, original_filename=filename)
            finally:
                temp_path.unlink(missing_ok=True)
                logger.info("Removed temporary uploaded file %s", temp_path)

    def _build_response(self, results: list[tuple]) -> ETLRunResponse:
        items = [
            ETLFileResult(
                ingestion_report_id=report.id,
                source_file=summary.source_file,
                raw_file=str(summary.raw_file),
                processed_file=str(summary.processed_file),
                rows_processed=summary.rows_processed,
                rows_skipped=summary.rows_skipped,
                clients_created=summary.clients_created,
                accounts_created=summary.accounts_created,
                assets_created=summary.assets_created,
                positions_upserted=summary.positions_upserted,
                detection_confidence=summary.detection_confidence,
                review_required=summary.review_required,
                review_status=report.review_status,
                review_reasons=list(summary.review_reasons),
            )
            for summary, report in results
        ]

        return ETLRunResponse(
            files_processed=len(items),
            total_rows_processed=sum(item.rows_processed for item in items),
            total_rows_skipped=sum(item.rows_skipped for item in items),
            results=items,
        )

    def _run_with_report(
        self,
        *,
        source_type: str,
        filename: str,
        detected_type: str,
        source_path: Path | None = None,
        s3_key: str | None = None,
        s3_prefix: str | None = None,
        s3_bucket_name: str | None = None,
        report_source_type: str | None = None,
    ) -> tuple:
        source_reference = str(source_path) if source_path is not None else (s3_key or s3_prefix or filename)
        try:
            summary = self.pipeline.run(
                source_path,
                source_type=source_type,
                s3_bucket_name=s3_bucket_name,
                s3_key=s3_key,
                s3_prefix=s3_prefix,
            )
            message = f"Arquivo {filename} processado com sucesso."
            resolved_detected_type = detect_ingestion_type(summary.source_file)
            report = self.ingestion_reports.create_success_report(
                summary=summary,
                filename=filename,
                source_type=report_source_type or source_type,
                detected_type=resolved_detected_type,
                message=message,
            )
            self.alerts.notify_ingestion_report(report)
            return summary, report
        except ApplicationError as exc:
            report = self.ingestion_reports.create_failure_report(
                filename=filename,
                source_file=source_reference,
                source_type=report_source_type or source_type,
                detected_type=detected_type,
                message=exc.message,
            )
            self.alerts.notify_ingestion_report(report)
            raise
        except Exception as exc:
            report = self.ingestion_reports.create_failure_report(
                filename=filename,
                source_file=source_reference,
                source_type=report_source_type or source_type,
                detected_type=detected_type,
                message=str(exc) or "Unexpected ingestion failure.",
            )
            self.alerts.notify_ingestion_report(report)
            raise

    def _resolve_local_files(self, source_path: str | None) -> list[Path]:
        if source_path:
            path = Path(source_path).expanduser().resolve()
            if not path.exists():
                raise ResourceNotFoundError(f"Input file not found: {path}")
            return [path]

        raw_files = discover_input_files(self.settings.raw_data_dir)
        if raw_files:
            return raw_files

        sample_files = discover_input_files(self.settings.samples_dir)
        if sample_files:
            return sample_files

        real_input_files = discover_input_files(self.settings.real_inputs_dir)
        if real_input_files:
            return [self.settings.real_inputs_dir]

        raise ResourceNotFoundError("No supported input files were found in data/raw, data/samples, or data/real_inputs.")

    def _resolve_reprocess_source(self, report: IngestionReport) -> tuple[str, Path | None, str | None]:
        for reference in [report.raw_file, report.source_file]:
            if not reference:
                continue
            if reference.startswith("s3://"):
                return "s3", None, self._extract_s3_key(reference)
            candidate = Path(reference).expanduser()
            if candidate.exists():
                return "local", candidate.resolve(), None

        raise ResourceNotFoundError(
            f"Unable to locate a durable source to reprocess ingestion report {report.id}. "
            "Expected a local raw file path or an s3:// reference."
        )

    @staticmethod
    def _extract_s3_key(source_uri: str) -> str:
        _, _, remainder = source_uri.partition("s3://")
        bucket, _, key = remainder.partition("/")
        if not bucket or not key:
            raise ETLInputError(f"Invalid S3 source reference for reprocessing: {source_uri}")
        return key

    @staticmethod
    def _detect_uploaded_type(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return "csv"
        if suffix in {".xlsx", ".xls"}:
            return "excel"
        if suffix == ".json":
            return "json"
        return suffix.lstrip(".") or "unknown"
