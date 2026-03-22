from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, Float, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.trading_enums import ImportJobStatus, TradeSourceType


def _enum_values(enum_cls) -> list[str]:
    return [item.value for item in enum_cls]


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("batch_id", name="uq_import_jobs_batch_id"),
        CheckConstraint("total_trades >= 0", name="ck_import_jobs_total_trades_non_negative"),
        CheckConstraint("imported_trades >= 0", name="ck_import_jobs_imported_trades_non_negative"),
        CheckConstraint("rejected_trades >= 0", name="ck_import_jobs_rejected_trades_non_negative"),
        CheckConstraint(
            "average_confidence_score IS NULL OR (average_confidence_score >= 0 AND average_confidence_score <= 1)",
            name="ck_import_jobs_confidence_score_range",
        ),
        CheckConstraint(
            "estimated_total_fees >= 0",
            name="ck_import_jobs_estimated_total_fees_non_negative",
        ),
        Index("ix_import_jobs_status_created_at", "status", "created_at"),
        Index("ix_import_jobs_source_type_created_at", "source_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[TradeSourceType] = mapped_column(
        SAEnum(
            TradeSourceType,
            name="import_job_source_type",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[ImportJobStatus] = mapped_column(
        SAEnum(
            ImportJobStatus,
            name="import_job_status",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ImportJobStatus.PENDING,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_total_fees: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False, default=Decimal("0.00"))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    trades: Mapped[list["Trade"]] = relationship(back_populates="import_job")
