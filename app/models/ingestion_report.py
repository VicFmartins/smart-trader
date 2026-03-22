from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestionReport(Base):
    __tablename__ = "ingestion_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    detected_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    layout_signature: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    raw_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    processed_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_required", index=True)
    review_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    detected_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    applied_mappings: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    structure_detection: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    rows_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reprocessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reprocess_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
