from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import clear_settings_cache
from app.core.exceptions import ETLInputError
from app.db.base import Base
from app.etl.contracts import ETLFileSummary
from app.models.ingestion_report import IngestionReport
from app.services.alert_service import AlertService
from app.services.etl_service import ETLService


class RecordingProvider:
    def __init__(self) -> None:
        self.payloads = []

    def publish(self, payload) -> None:
        self.payloads.append(payload)


class FailingProvider:
    def publish(self, payload) -> None:
        raise RuntimeError("sns unavailable")


class RecordingAlerts:
    def __init__(self) -> None:
        self.reports = []

    def notify_ingestion_report(self, report: IngestionReport) -> bool:
        self.reports.append(report)
        return True


@pytest.fixture
def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "alerts_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    clear_settings_cache()

    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        clear_settings_cache()


def test_alert_service_does_not_publish_when_disabled() -> None:
    provider = RecordingProvider()
    service = AlertService(enabled=False, provider_name="log", provider=provider)

    published = service.notify_ingestion_report(_build_report(status="error", review_required=True))

    assert published is False
    assert provider.payloads == []


def test_alert_service_publishes_review_required_payload() -> None:
    provider = RecordingProvider()
    service = AlertService(enabled=True, provider_name="log", provider=provider)

    published = service.notify_ingestion_report(_build_report(status="review_required", review_required=True))

    assert published is True
    assert len(provider.payloads) == 1
    payload = provider.payloads[0]
    assert payload.event_type == "ingestion_review_required"
    assert payload.ingestion_report_id == 17
    assert payload.filename == "carteira.csv"
    assert payload.review_reasons == ["missing_reference_date"]


def test_alert_service_provider_failure_does_not_raise() -> None:
    service = AlertService(enabled=True, provider_name="sns", provider=FailingProvider())

    published = service.notify_ingestion_report(_build_report(status="error", review_required=True))

    assert published is False


def test_etl_service_triggers_alert_on_review_required_run(
    db_session: Session,
    tmp_path: Path,
) -> None:
    service = ETLService(db_session)
    service.alerts = RecordingAlerts()
    summary = _build_summary(
        tmp_path=tmp_path,
        source_file=str(tmp_path / "review_required.csv"),
        review_required=True,
        review_reasons=("missing_reference_date",),
        detection_confidence=0.48,
    )
    service.pipeline.run = lambda *args, **kwargs: summary

    _, report = service._run_with_report(
        source_type="local",
        source_path=tmp_path / "review_required.csv",
        filename="review_required.csv",
        detected_type="csv",
    )

    assert report.status == "review_required"
    assert report.review_required is True
    assert len(service.alerts.reports) == 1
    assert service.alerts.reports[0].id == report.id


def test_etl_service_triggers_alert_on_failed_run(
    db_session: Session,
    tmp_path: Path,
) -> None:
    service = ETLService(db_session)
    service.alerts = RecordingAlerts()

    def fail_pipeline(*args, **kwargs):
        raise ETLInputError("Arquivo inconsistente.")

    service.pipeline.run = fail_pipeline

    with pytest.raises(ETLInputError):
        service._run_with_report(
            source_type="local",
            source_path=tmp_path / "broken.csv",
            filename="broken.csv",
            detected_type="csv",
        )

    assert len(service.alerts.reports) == 1
    assert service.alerts.reports[0].status == "error"
    assert service.alerts.reports[0].filename == "broken.csv"


def test_etl_service_continues_when_alert_delivery_fails(
    db_session: Session,
    tmp_path: Path,
) -> None:
    service = ETLService(db_session)
    service.alerts = AlertService(enabled=True, provider_name="sns", provider=FailingProvider())
    summary = _build_summary(
        tmp_path=tmp_path,
        source_file=str(tmp_path / "alert_failure.csv"),
        review_required=True,
        review_reasons=("missing_reference_date",),
        detection_confidence=0.51,
    )
    service.pipeline.run = lambda *args, **kwargs: summary

    _, report = service._run_with_report(
        source_type="local",
        source_path=tmp_path / "alert_failure.csv",
        filename="alert_failure.csv",
        detected_type="csv",
    )

    assert report.status == "review_required"
    assert report.review_required is True


def _build_report(*, status: str, review_required: bool) -> IngestionReport:
    return IngestionReport(
        id=17,
        filename="carteira.csv",
        source_file="s3://carteiraconsol-raw/incoming/carteira.csv",
        source_type="lambda_s3",
        detected_type="csv",
        layout_signature="ativo|cliente|quantidade",
        raw_file="s3://carteiraconsol-raw/incoming/carteira.csv",
        processed_file="data/processed/normalized.csv",
        parser_name="smart_tabular_reader",
        detection_confidence=0.42,
        review_required=review_required,
        review_status="pending" if review_required else "not_required",
        review_reasons=["missing_reference_date"],
        detected_columns=["cliente", "ativo", "quantidade"],
        applied_mappings=[],
        structure_detection={"header_row_index": 2},
        rows_processed=1,
        rows_skipped=0,
        status=status,
        message="Arquivo requer revisao.",
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
        reprocessed_at=None,
        reprocess_count=0,
    )


def _build_summary(
    *,
    tmp_path: Path,
    source_file: str,
    review_required: bool,
    review_reasons: tuple[str, ...],
    detection_confidence: float | None,
) -> ETLFileSummary:
    raw_file = tmp_path / "raw.csv"
    processed_file = tmp_path / "processed.csv"
    raw_file.write_text("raw", encoding="utf-8")
    processed_file.write_text("processed", encoding="utf-8")
    return ETLFileSummary(
        source_file=source_file,
        raw_file=raw_file,
        processed_file=processed_file,
        rows_processed=1,
        rows_skipped=0,
        clients_created=1,
        accounts_created=1,
        assets_created=1,
        positions_upserted=1,
        detection_confidence=detection_confidence,
        review_required=review_required,
        review_reasons=review_reasons,
        parser_name="smart_tabular_reader",
        layout_signature="ativo|cliente|quantidade",
        detected_columns=("cliente", "ativo", "quantidade"),
        applied_mappings=(),
        structure_detection={"header_row_index": 2},
    )
