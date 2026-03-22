from datetime import date
from decimal import Decimal

import pandas as pd

from app.etl.transform.parsers import parse_decimal, parse_reference_date


def test_parse_decimal_handles_brazilian_and_international_formats() -> None:
    assert parse_decimal("10.250,33") == Decimal("10250.33")
    assert parse_decimal("10,250.33") == Decimal("10250.33")
    assert parse_decimal("1 250,10") == Decimal("1250.10")
    assert parse_decimal("(1.234,56)") == Decimal("-1234.56")
    assert parse_decimal("0.12345678") == Decimal("0.12345678")


def test_parse_reference_date_handles_multiple_formats() -> None:
    excel_serial = (pd.Timestamp("2026-03-15") - pd.Timestamp("1899-12-30")).days

    assert parse_reference_date("15/03/2026") == date(2026, 3, 15)
    assert parse_reference_date("03/15/2026") == date(2026, 3, 15)
    assert parse_reference_date("2026-03-15") == date(2026, 3, 15)
    assert parse_reference_date(excel_serial) == date(2026, 3, 15)
