from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import ORMModel

VALID_REVIEW_STATUSES = {"pending", "approved", "rejected", "not_required"}


class IngestionReportRead(ORMModel):
    id: int
    filename: str
    source_file: str
    source_type: str
    detected_type: str
    layout_signature: str | None = None
    raw_file: str | None = None
    processed_file: str | None = None
    parser_name: str | None = None
    detection_confidence: float | None = None
    review_required: bool
    review_status: str
    review_reasons: list[str] = Field(default_factory=list)
    detected_columns: list[str] = Field(default_factory=list)
    applied_mappings: list[dict[str, object]] = Field(default_factory=list)
    structure_detection: dict[str, object] = Field(default_factory=dict)
    rows_processed: int = Field(ge=0)
    rows_skipped: int = Field(ge=0)
    status: str
    message: str
    created_at: datetime
    processed_at: datetime | None = None
    reprocessed_at: datetime | None = None
    reprocess_count: int = Field(ge=0)


class IngestionReportReviewUpdate(ORMModel):
    review_status: str = Field(description="pending, approved, rejected, or not_required")
    approved_by: str | None = None

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_REVIEW_STATUSES:
            raise ValueError(f"review_status must be one of: {sorted(VALID_REVIEW_STATUSES)}")
        return normalized
