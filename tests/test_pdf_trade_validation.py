from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.schemas.pdf_import import BrokerDetectionResult, LLMTradeExtractionPayload, PDFAssetClassification, ReviewWarningSeverity
from app.services.pdf_import.validation import (
    TradeExtractionNormalizer,
    classify_asset_ticker,
    normalize_decimal_value,
    normalize_quantity,
    normalize_trade_date,
    normalize_trade_time,
)


def test_classify_asset_ticker_detects_standard_and_non_standard_tickers() -> None:
    ticker, classification, warnings = classify_asset_ticker("winj26")

    assert ticker == "WINJ26"
    assert classification == PDFAssetClassification.WIN
    assert warnings == []

    ticker, classification, warnings = classify_asset_ticker("abc123")

    assert ticker == "ABC123"
    assert classification == PDFAssetClassification.OTHER
    assert warnings[0].code == "non_standard_asset_ticker"


def test_normalize_helpers_parse_dates_times_and_decimals() -> None:
    trade_date, date_warnings = normalize_trade_date("21/03/2026")
    trade_time, time_warnings = normalize_trade_time("930")
    entry_price, price_warnings = normalize_decimal_value("1.234,56", field="entry_price", positive_only=True)

    assert trade_date == date(2026, 3, 21)
    assert date_warnings == []
    assert trade_time == "09:30:00"
    assert time_warnings == []
    assert entry_price == Decimal("1234.56")
    assert price_warnings == []


def test_trade_normalizer_collects_warnings_and_rejects_impossible_values() -> None:
    payload = LLMTradeExtractionPayload.model_validate(
        {
            "broker": None,
            "document_date": "2026-03-21",
            "warnings": ["llm noticed merged rows"],
            "trades": [
                {
                    "trade_date": None,
                    "asset": "WINX26",
                    "asset_class": "WIN",
                    "operation_type": "BUY",
                    "quantity": "500",
                    "entry_price": "125.000,50",
                    "exit_price": None,
                    "gross_result": None,
                    "fees": "3,50",
                    "net_result": None,
                    "trade_time": "9:3A",
                    "confidence_score": 0.83,
                    "source_page": 1,
                },
                {
                    "trade_date": "99/99/2026",
                    "asset": "XYZ",
                    "asset_class": "WDO",
                    "operation_type": "???",
                    "quantity": "-1",
                    "entry_price": "0",
                    "exit_price": "-10",
                    "gross_result": "10",
                    "fees": "-1",
                    "trade_time": "28:00",
                    "confidence_score": 2,
                    "source_page": "0",
                },
            ],
        }
    )

    result = TradeExtractionNormalizer().normalize(
        payload=payload,
        filename="nota_teste.pdf",
        broker_detection=BrokerDetectionResult(broker=None, confidence=0, strategy="unknown", evidence=[]),
    )

    assert result.normalized_trade_date == date(2026, 3, 21)
    assert any(warning.code == "unknown_broker" for warning in result.warnings)
    assert any(warning.code == "llm_warning" for warning in result.warnings)

    first_trade = result.trades[0]
    assert first_trade.asset_ticker == "WINX26"
    assert first_trade.asset_classification == PDFAssetClassification.WIN
    assert first_trade.trade_date == date(2026, 3, 21)
    assert first_trade.trade_time is None
    assert first_trade.quantity == 500
    assert first_trade.entry_price == Decimal("125000.50000")
    assert first_trade.exit_price is None
    assert first_trade.confidence_score == 0.83
    assert first_trade.ready_for_persistence is False
    assert any(warning.code == "suspicious_quantity" for warning in first_trade.warnings)
    assert any(warning.code == "missing_exit_price" for warning in first_trade.warnings)
    assert any(warning.code == "invalid_time_format" for warning in first_trade.warnings)

    second_trade = result.trades[1]
    assert second_trade.asset_classification == PDFAssetClassification.OTHER
    assert second_trade.ready_for_persistence is False
    assert second_trade.rejection_reasons
    assert any(warning.severity == ReviewWarningSeverity.ERROR for warning in second_trade.warnings)
    assert any(warning.code == "invalid_operation_type" for warning in second_trade.warnings)
    assert any(warning.code == "invalid_quantity" for warning in second_trade.warnings)
    assert any(warning.code == "invalid_entry_price" for warning in second_trade.warnings)


def test_normalize_quantity_rejects_non_numeric() -> None:
    quantity, warnings = normalize_quantity("abc")

    assert quantity is None
    assert warnings[0].code == "invalid_quantity"
