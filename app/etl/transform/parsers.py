from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd


BLANK_MARKERS = {
    "",
    "-",
    "--",
    "---",
    "n/a",
    "na",
    "nan",
    "null",
    "none",
    "sem dados",
    "sem informacao",
    "sem informação",
}

CURRENCY_TOKENS = ("R$", "US$", "USD", "BRL", "EUR", "€", "$")
DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y%m%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d/%m/%y",
)
EXCEL_EPOCH = pd.Timestamp("1899-12-30")


def is_blankish(value: object) -> bool:
    if value is None or pd.isna(value):
        return True
    text = str(value).strip()
    return not text or text.lower() in BLANK_MARKERS


def slugify_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", " ", ascii_text).strip().lower()


def normalize_lookup_text(value: object, default: str) -> str:
    if is_blankish(value):
        return default
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", ascii_text).strip().upper()
    return text or default


def normalize_text(value: object, default: str) -> str:
    if is_blankish(value):
        return default
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or default


def parse_decimal(value: object) -> Decimal | None:
    if is_blankish(value):
        return None

    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    for token in CURRENCY_TOKENS:
        text = text.replace(token, "")

    text = text.replace("%", "")
    text = text.replace("'", "")

    is_negative = False
    if text.startswith("(") and text.endswith(")"):
        is_negative = True
        text = text[1:-1]
    if text.endswith("-"):
        is_negative = True
        text = text[:-1]
    if text.startswith("-"):
        is_negative = True
        text = text[1:]

    normalized = _normalize_number_text(text)
    if not normalized:
        return None

    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    return -parsed if is_negative else parsed


def _normalize_number_text(text: str) -> str:
    comma_count = text.count(",")
    dot_count = text.count(".")

    if comma_count and dot_count:
        decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        return text.replace(thousands_separator, "").replace(decimal_separator, ".")

    if comma_count:
        return _normalize_single_separator(text, ",")

    if dot_count:
        return _normalize_single_separator(text, ".")

    return text


def _normalize_single_separator(text: str, separator: str) -> str:
    parts = text.split(separator)
    if len(parts) == 1:
        return text

    trailing = parts[-1]
    leading = "".join(parts[:-1])
    separator_count = len(parts) - 1

    if separator_count > 1:
        if all(len(part) == 3 for part in parts[1:]):
            return leading + trailing
        return leading + "." + trailing

    if separator == ",":
        if len(trailing) == 3 and len(leading) > 3:
            return leading + trailing
        return leading + "." + trailing

    if len(trailing) == 3 and len(leading) > 3:
        return leading + trailing
    return text


def parse_reference_date(value: object) -> date | None:
    if is_blankish(value):
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    serial_date = _parse_excel_serial_date(value)
    if serial_date is not None:
        return serial_date

    text = normalize_text(value, "")
    if not text:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    dayfirst_preferred = _should_prefer_dayfirst(text)
    for dayfirst in (dayfirst_preferred, not dayfirst_preferred):
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
        if not pd.isna(parsed):
            return parsed.date()

    return None


def _parse_excel_serial_date(value: object) -> date | None:
    numeric_value = parse_decimal(value)
    if numeric_value is None:
        return None
    if numeric_value != numeric_value.to_integral_value():
        return None

    serial = int(numeric_value)
    if not 20_000 <= serial <= 80_000:
        return None

    return (EXCEL_EPOCH + pd.to_timedelta(serial, unit="D")).date()


def _should_prefer_dayfirst(text: str) -> bool:
    match = re.match(r"^\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\s*$", text)
    if not match:
        return True

    first = int(match.group(1))
    second = int(match.group(2))
    if first > 12:
        return True
    if second > 12:
        return False
    return True
