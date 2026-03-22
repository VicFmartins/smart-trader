from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accepted_column_mapping import AcceptedColumnMapping
from app.models.ingestion_report import IngestionReport
from app.etl.detect.column_mapper import build_layout_signature


class AcceptedMappingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_preferred_mappings(
        self,
        *,
        layout_signature: str,
        institution_name: str | None = None,
    ) -> dict[str, str]:
        if not layout_signature:
            return {}

        statement = select(AcceptedColumnMapping).where(AcceptedColumnMapping.layout_signature == layout_signature)
        if institution_name:
            items = list(
                self.db.scalars(
                    statement.where(
                        (AcceptedColumnMapping.institution_name == institution_name)
                        | (AcceptedColumnMapping.institution_name.is_(None))
                    )
                ).all()
            )
        else:
            items = list(self.db.scalars(statement).all())

        preferred: dict[str, str] = {}
        for item in items:
            preferred[item.source_column] = item.canonical_field
        return preferred

    def persist_from_report(self, report: IngestionReport, *, approved_by: str | None = None) -> list[AcceptedColumnMapping]:
        mappings = report.applied_mappings or []
        layout_signature = report.layout_signature or build_layout_signature(report.detected_columns or [])
        if not mappings or not layout_signature:
            return []

        persisted: list[AcceptedColumnMapping] = []
        for mapping in mappings:
            if not mapping.get("accepted"):
                continue
            source_column = str(mapping.get("normalized_name") or "")
            canonical_field = str(mapping.get("canonical_name") or "")
            if not source_column or not canonical_field:
                continue

            existing = self.db.scalar(
                select(AcceptedColumnMapping).where(
                    AcceptedColumnMapping.institution_name.is_(None),
                    AcceptedColumnMapping.layout_signature == layout_signature,
                    AcceptedColumnMapping.source_column == source_column,
                )
            )
            if existing is None:
                existing = AcceptedColumnMapping(
                    institution_name=None,
                    layout_signature=layout_signature,
                    source_column=source_column,
                    canonical_field=canonical_field,
                    confidence=float(mapping.get("score") or 0.0),
                    approved_by=approved_by,
                )
                self.db.add(existing)
            else:
                existing.canonical_field = canonical_field
                existing.confidence = float(mapping.get("score") or 0.0)
                existing.approved_by = approved_by
                existing.updated_at = datetime.now(UTC)
            persisted.append(existing)

        self.db.flush()
        return persisted
