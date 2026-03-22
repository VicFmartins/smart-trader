from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass(slots=True, frozen=True)
class PositionRecord:
    client_name: str
    broker: str
    original_name: str
    normalized_name: str
    ticker: str | None
    quantity: Decimal
    avg_price: Decimal
    total_value: Decimal
    reference_date: date
    risk_profile: str
    asset_class: str
    cnpj: str | None
    maturity_date: date | None


@dataclass(slots=True, frozen=True)
class ETLFileSummary:
    source_file: str
    raw_file: str | Path
    processed_file: Path
    rows_processed: int
    rows_skipped: int
    clients_created: int
    accounts_created: int
    assets_created: int
    positions_upserted: int
    detection_confidence: float | None = None
    review_required: bool = False
    review_reasons: tuple[str, ...] = ()
    parser_name: str | None = None
    layout_signature: str | None = None
    detected_columns: tuple[str, ...] = ()
    applied_mappings: tuple[dict[str, object], ...] = ()
    structure_detection: dict[str, object] | None = None
