from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AcceptedColumnMapping(Base):
    __tablename__ = "accepted_column_mappings"
    __table_args__ = (
        UniqueConstraint(
            "institution_name",
            "layout_signature",
            "source_column",
            name="uq_accepted_column_mapping_signature_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    layout_signature: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    source_column: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_field: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
