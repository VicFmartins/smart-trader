from __future__ import annotations

import json
import logging
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import boto3

from app.core.config import get_settings
from app.models.ingestion_report import IngestionReport


logger = logging.getLogger(__name__)


class AlertProvider(Protocol):
    def publish(self, payload: "AlertPayload") -> None: ...


@dataclass(frozen=True, slots=True)
class AlertPayload:
    event_type: str
    severity: str
    ingestion_report_id: int
    filename: str
    source_type: str
    detected_type: str
    status: str
    review_status: str
    review_required: bool
    review_reasons: list[str]
    detection_confidence: float | None
    raw_file: str | None
    parser_name: str | None
    message: str
    processed_at: str | None

    @classmethod
    def from_report(cls, report: IngestionReport) -> "AlertPayload | None":
        if report.status == "error":
            return cls(
                event_type="ingestion_failed",
                severity="error",
                ingestion_report_id=report.id,
                filename=report.filename,
                source_type=report.source_type,
                detected_type=report.detected_type,
                status=report.status,
                review_status=report.review_status,
                review_required=report.review_required,
                review_reasons=list(report.review_reasons or []),
                detection_confidence=report.detection_confidence,
                raw_file=report.raw_file,
                parser_name=report.parser_name,
                message=report.message,
                processed_at=_format_datetime(report.processed_at),
            )
        if report.review_required:
            return cls(
                event_type="ingestion_review_required",
                severity="warning",
                ingestion_report_id=report.id,
                filename=report.filename,
                source_type=report.source_type,
                detected_type=report.detected_type,
                status=report.status,
                review_status=report.review_status,
                review_required=report.review_required,
                review_reasons=list(report.review_reasons or []),
                detection_confidence=report.detection_confidence,
                raw_file=report.raw_file,
                parser_name=report.parser_name,
                message=report.message,
                processed_at=_format_datetime(report.processed_at),
            )
        return None


class NoOpAlertProvider:
    def publish(self, payload: AlertPayload) -> None:
        logger.debug(
            "Operational alerts disabled. Skipping %s for ingestion report %s.",
            payload.event_type,
            payload.ingestion_report_id,
        )


class LogAlertProvider:
    def publish(self, payload: AlertPayload) -> None:
        logger.warning(
            "Operational alert %s for ingestion report %s (%s): %s",
            payload.event_type,
            payload.ingestion_report_id,
            payload.filename,
            payload.message,
            extra={"alert_payload": asdict(payload)},
        )


class SNSAlertProvider:
    def __init__(self, *, topic_arn: str, sns_client=None) -> None:
        self.topic_arn = topic_arn
        self.sns_client = sns_client or boto3.client("sns")

    def publish(self, payload: AlertPayload) -> None:
        subject = f"[{get_settings().project_name}] {payload.event_type}: {payload.filename}"
        self.sns_client.publish(
            TopicArn=self.topic_arn,
            Subject=subject[:100],
            Message=json.dumps(asdict(payload), ensure_ascii=True, default=str),
        )


class AlertService:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        provider_name: str | None = None,
        topic_arn: str | None = None,
        provider: AlertProvider | None = None,
        sns_client=None,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.alerts_enabled if enabled is None else enabled
        self.provider_name = settings.alert_provider if provider_name is None else provider_name
        self.topic_arn = settings.alert_sns_topic_arn if topic_arn is None else topic_arn
        self.provider = provider or self._build_provider(sns_client=sns_client)

    def notify_ingestion_report(self, report: IngestionReport) -> bool:
        payload = AlertPayload.from_report(report)
        if payload is None or not self.enabled:
            return False

        try:
            self.provider.publish(payload)
            logger.info(
                "Published operational alert %s for ingestion report %s.",
                payload.event_type,
                payload.ingestion_report_id,
            )
            return True
        except Exception:
            logger.exception(
                "Failed to publish operational alert %s for ingestion report %s.",
                payload.event_type,
                payload.ingestion_report_id,
            )
            return False

    def _build_provider(self, *, sns_client=None) -> AlertProvider:
        if self.provider_name == "sns":
            if not self.topic_arn:
                logger.warning(
                    "ALERT_PROVIDER is set to sns but ALERT_SNS_TOPIC_ARN is empty. Falling back to log alerts."
                )
                return LogAlertProvider()
            return SNSAlertProvider(topic_arn=self.topic_arn, sns_client=sns_client)
        if self.provider_name == "log":
            return LogAlertProvider()
        return NoOpAlertProvider()


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
