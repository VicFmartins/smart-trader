from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from app.etl.transform.parsers import parse_decimal, parse_reference_date


def parse_brazilian_decimal(value: object) -> Decimal | None:
    return parse_decimal(value)


def parse_flexible_date(value: object) -> date | None:
    return parse_reference_date(value)


def cleanup_ticker(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    cleaned = re.sub(r"[^A-Z0-9]", "", text)
    return cleaned or None
