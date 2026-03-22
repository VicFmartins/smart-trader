from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.schemas.pdf_import import (
    BrokerDetectionResult,
    LLMTradeExtractionItem,
    LLMTradeExtractionPayload,
    PDFAssetClassification,
    ReviewableTrade,
    TradeReviewWarning,
    ReviewWarningSeverity,
)


STANDARD_FUTURES_TICKER_PATTERN = re.compile(r"^(WIN|WDO)([FGHJKMNQUVXZ]\d{1,2})?$", re.IGNORECASE)
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")
TIME_PATTERN = re.compile(r"^(?P<hour>\d{1,2})(?::?(?P<minute>\d{2}))(?::?(?P<second>\d{2}))?$")
MAX_REASONABLE_QUANTITY = 200
MAX_ABSOLUTE_QUANTITY = 100000


@dataclass(frozen=True, slots=True)
class NormalizedTradeReviewResult:
    normalized_broker: str | None
    normalized_trade_date: date | None
    trades: list[ReviewableTrade]
    warnings: list[TradeReviewWarning]


def classify_asset_ticker(raw_ticker: object) -> tuple[str | None, PDFAssetClassification, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    ticker = _normalize_string(raw_ticker)
    if ticker is None:
        warnings.append(_warning("missing_asset_ticker", "Asset ticker is missing.", field="asset"))
        return None, PDFAssetClassification.OTHER, warnings

    normalized = re.sub(r"[^A-Z0-9]", "", ticker.upper())
    if not normalized:
        warnings.append(_warning("missing_asset_ticker", "Asset ticker is missing.", field="asset"))
        return None, PDFAssetClassification.OTHER, warnings

    if normalized.startswith("WIN"):
        classification = PDFAssetClassification.WIN
    elif normalized.startswith("WDO"):
        classification = PDFAssetClassification.WDO
    else:
        classification = PDFAssetClassification.OTHER

    if not STANDARD_FUTURES_TICKER_PATTERN.match(normalized):
        warnings.append(
            _warning(
                "non_standard_asset_ticker",
                f"Asset ticker '{normalized}' does not match the standard WIN/WDO contract format.",
                field="asset",
            )
        )
    return normalized, classification, warnings


def normalize_trade_date(raw_value: object) -> tuple[date | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    normalized = _normalize_string(raw_value)
    if normalized is None:
        return None, warnings

    for fmt in DATE_FORMATS:
        try:
            from datetime import datetime

            return datetime.strptime(normalized, fmt).date(), warnings
        except ValueError:
            continue

    warnings.append(_warning("invalid_trade_date", f"Invalid trade date format '{normalized}'.", field="trade_date"))
    return None, warnings


def normalize_trade_time(raw_value: object) -> tuple[str | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    normalized = _normalize_string(raw_value)
    if normalized is None:
        return None, warnings

    collapsed = normalized.replace(".", ":").replace("-", ":").replace(" ", "")
    match = TIME_PATTERN.match(collapsed)
    if match is None:
        warnings.append(_warning("invalid_time_format", f"Invalid time format '{normalized}'.", field="trade_time"))
        return None, warnings

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = int(match.group("second") or 0)
    if hour > 23 or minute > 59 or second > 59:
        warnings.append(_warning("invalid_time_format", f"Invalid time format '{normalized}'.", field="trade_time"))
        return None, warnings

    return f"{hour:02d}:{minute:02d}:{second:02d}", warnings


def normalize_decimal_value(
    raw_value: object,
    *,
    field: str,
    positive_only: bool = False,
    non_negative: bool = False,
    scale: str = "0.01",
) -> tuple[Decimal | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    if raw_value is None:
        return None, warnings

    try:
        normalized_string = _normalize_numeric_string(raw_value)
        decimal_value = Decimal(normalized_string).quantize(Decimal(scale), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        warnings.append(_warning(f"invalid_{field}", f"Invalid numeric value for {field}.", field=field))
        return None, warnings

    if positive_only and decimal_value <= 0:
        warnings.append(_error(f"invalid_{field}", f"{field} must be greater than zero.", field=field))
        return None, warnings
    if non_negative and decimal_value < 0:
        warnings.append(_error(f"invalid_{field}", f"{field} must be zero or greater.", field=field))
        return None, warnings
    return decimal_value, warnings


def normalize_quantity(raw_value: object) -> tuple[int | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    if raw_value is None:
        warnings.append(_error("missing_quantity", "Quantity is missing.", field="quantity"))
        return None, warnings

    try:
        quantity_decimal = Decimal(_normalize_numeric_string(raw_value))
    except (InvalidOperation, ValueError):
        warnings.append(_error("invalid_quantity", "Quantity must be numeric.", field="quantity"))
        return None, warnings

    if quantity_decimal != quantity_decimal.to_integral_value():
        warnings.append(_error("invalid_quantity", "Quantity must be a whole number.", field="quantity"))
        return None, warnings

    quantity = int(quantity_decimal)
    if quantity <= 0:
        warnings.append(_error("invalid_quantity", "Quantity must be greater than zero.", field="quantity"))
        return None, warnings
    if quantity > MAX_ABSOLUTE_QUANTITY:
        warnings.append(_error("suspicious_quantity", "Quantity is too large to be accepted automatically.", field="quantity"))
        return None, warnings
    if quantity > MAX_REASONABLE_QUANTITY:
        warnings.append(_warning("suspicious_quantity", "Quantity looks unusually high for a mini contract trade.", field="quantity"))
    return quantity, warnings


def normalize_operation_type(raw_value: object) -> tuple[str | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    normalized = _normalize_string(raw_value)
    if normalized is None:
        warnings.append(_error("missing_operation_type", "Operation type is missing.", field="operation_type"))
        return None, warnings

    upper = normalized.upper()
    if upper in {"BUY", "COMPRA", "C"}:
        return "buy", warnings
    if upper in {"SELL", "VENDA", "V"}:
        return "sell", warnings

    warnings.append(_error("invalid_operation_type", f"Unknown operation type '{normalized}'.", field="operation_type"))
    return None, warnings


def normalize_broker_name(raw_value: object) -> tuple[str | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    normalized = _normalize_string(raw_value)
    if normalized is None:
        warnings.append(_warning("unknown_broker", "Broker could not be determined.", field="broker"))
        return None, warnings
    return normalized.upper(), warnings


def normalize_confidence_score(raw_value: object) -> tuple[float | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    if raw_value is None:
        return None, warnings

    try:
        value = float(str(raw_value).replace(",", "."))
    except ValueError:
        warnings.append(_warning("invalid_confidence_score", "Confidence score is invalid.", field="confidence_score"))
        return None, warnings

    if value < 0 or value > 1:
        warnings.append(_warning("invalid_confidence_score", "Confidence score must be between 0 and 1.", field="confidence_score"))
        return None, warnings
    return value, warnings


def normalize_source_page(raw_value: object) -> tuple[int | None, list[TradeReviewWarning]]:
    warnings: list[TradeReviewWarning] = []
    if raw_value is None:
        return None, warnings
    try:
        value = int(Decimal(_normalize_numeric_string(raw_value)))
    except (InvalidOperation, ValueError):
        warnings.append(_warning("invalid_source_page", "Source page is invalid.", field="source_page"))
        return None, warnings
    if value < 1:
        warnings.append(_warning("invalid_source_page", "Source page must be at least 1.", field="source_page"))
        return None, warnings
    return value, warnings


class TradeExtractionNormalizer:
    def normalize(
        self,
        *,
        payload: LLMTradeExtractionPayload,
        filename: str,
        broker_detection: BrokerDetectionResult,
        import_batch_id: str | None = None,
    ) -> NormalizedTradeReviewResult:
        top_level_warnings: list[TradeReviewWarning] = []

        normalized_broker, broker_warnings = normalize_broker_name(payload.broker or broker_detection.broker)
        top_level_warnings.extend(broker_warnings)

        normalized_trade_date, trade_date_warnings = normalize_trade_date(payload.document_date)
        top_level_warnings.extend(trade_date_warnings)
        top_level_warnings.extend(
            TradeReviewWarning(code="llm_warning", message=warning)
            for warning in payload.warnings
            if warning.strip()
        )

        trades = [
            self._normalize_trade(
                trade=trade,
                trade_index=index,
                filename=filename,
                import_batch_id=import_batch_id,
                default_broker=normalized_broker,
                default_trade_date=normalized_trade_date,
            )
            for index, trade in enumerate(payload.trades)
        ]
        return NormalizedTradeReviewResult(
            normalized_broker=normalized_broker,
            normalized_trade_date=normalized_trade_date,
            trades=trades,
            warnings=top_level_warnings,
        )

    def _normalize_trade(
        self,
        *,
        trade: LLMTradeExtractionItem,
        trade_index: int,
        filename: str,
        import_batch_id: str | None,
        default_broker: str | None,
        default_trade_date: date | None,
    ) -> ReviewableTrade:
        warnings: list[TradeReviewWarning] = []

        asset_ticker, asset_classification, asset_warnings = classify_asset_ticker(trade.asset)
        warnings.extend(self._attach_trade_index(asset_warnings, trade_index))
        self._append_asset_class_mismatch_warning(
            warnings=warnings,
            trade_index=trade_index,
            raw_asset_class=trade.asset_class,
            normalized_asset_class=asset_classification,
        )

        trade_date, trade_date_warnings = normalize_trade_date(trade.trade_date)
        warnings.extend(self._attach_trade_index(trade_date_warnings, trade_index))
        if trade_date is None:
            trade_date = default_trade_date
        if trade_date is None:
            warnings.append(
                TradeReviewWarning(
                    code="missing_trade_date",
                    message="Trade date is missing.",
                    severity=ReviewWarningSeverity.ERROR,
                    field="trade_date",
                    trade_index=trade_index,
                )
            )

        trade_time, time_warnings = normalize_trade_time(trade.trade_time)
        warnings.extend(self._attach_trade_index(time_warnings, trade_index))

        operation_type, operation_warnings = normalize_operation_type(trade.operation_type)
        warnings.extend(self._attach_trade_index(operation_warnings, trade_index))

        quantity, quantity_warnings = normalize_quantity(trade.quantity)
        warnings.extend(self._attach_trade_index(quantity_warnings, trade_index))

        entry_price, entry_warnings = normalize_decimal_value(
            trade.entry_price,
            field="entry_price",
            positive_only=True,
            scale="0.00001",
        )
        warnings.extend(self._attach_trade_index(entry_warnings, trade_index))

        exit_price, exit_warnings = normalize_decimal_value(
            trade.exit_price,
            field="exit_price",
            positive_only=True,
            scale="0.00001",
        )
        warnings.extend(self._attach_trade_index(exit_warnings, trade_index))
        if trade.exit_price is None:
            warnings.append(
                TradeReviewWarning(
                    code="missing_exit_price",
                    message="Exit price is missing.",
                    field="exit_price",
                    trade_index=trade_index,
                )
            )

        gross_result, gross_warnings = normalize_decimal_value(trade.gross_result, field="gross_result", scale="0.01")
        warnings.extend(self._attach_trade_index(gross_warnings, trade_index))

        fees, fee_warnings = normalize_decimal_value(trade.fees, field="fees", non_negative=True, scale="0.01")
        warnings.extend(self._attach_trade_index(fee_warnings, trade_index))

        net_result, net_warnings = normalize_decimal_value(trade.net_result, field="net_result", scale="0.01")
        warnings.extend(self._attach_trade_index(net_warnings, trade_index))

        broker, broker_warnings = normalize_broker_name(trade.broker or default_broker)
        warnings.extend(self._attach_trade_index(broker_warnings, trade_index))

        confidence_score, confidence_warnings = normalize_confidence_score(trade.confidence_score)
        warnings.extend(self._attach_trade_index(confidence_warnings, trade_index))

        source_page, source_page_warnings = normalize_source_page(trade.source_page)
        warnings.extend(self._attach_trade_index(source_page_warnings, trade_index))

        rejection_reasons = [warning.message for warning in warnings if warning.severity == ReviewWarningSeverity.ERROR]
        ready_for_persistence = (
            not rejection_reasons
            and not warnings
            and asset_classification in {PDFAssetClassification.WIN, PDFAssetClassification.WDO}
            and asset_ticker is not None
            and trade_date is not None
            and operation_type is not None
            and quantity is not None
            and entry_price is not None
        )

        return ReviewableTrade(
            trade_index=trade_index,
            trade_date=trade_date,
            trade_time=trade_time,
            asset_ticker=asset_ticker,
            asset_classification=asset_classification,
            operation_type=operation_type,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            gross_result=gross_result,
            fees=fees,
            net_result=net_result,
            broker=broker,
            imported_file_name=filename,
            import_batch_id=import_batch_id,
            notes=trade.notes,
            confidence_score=confidence_score,
            source_page=source_page,
            warnings=warnings,
            rejection_reasons=rejection_reasons,
            ready_for_review=True,
            ready_for_persistence=ready_for_persistence,
        )

    def _attach_trade_index(self, warnings: list[TradeReviewWarning], trade_index: int) -> list[TradeReviewWarning]:
        return [
            warning.model_copy(update={"trade_index": trade_index}) if warning.trade_index is None else warning
            for warning in warnings
        ]

    def _append_asset_class_mismatch_warning(
        self,
        *,
        warnings: list[TradeReviewWarning],
        trade_index: int,
        raw_asset_class: str | None,
        normalized_asset_class: PDFAssetClassification,
    ) -> None:
        raw_normalized = _normalize_string(raw_asset_class)
        if raw_normalized is None:
            return
        expected = normalized_asset_class.value
        if raw_normalized.upper() != expected:
            warnings.append(
                TradeReviewWarning(
                    code="asset_class_mismatch",
                    message=f"Asset classification '{raw_normalized}' does not match normalized classification '{expected}'.",
                    field="asset_class",
                    trade_index=trade_index,
                )
            )


def _normalize_string(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_numeric_string(value: object) -> str:
    raw = _normalize_string(value)
    if raw is None:
        raise ValueError("Missing numeric value.")
    normalized = raw.replace("R$", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    return normalized


def _warning(code: str, message: str, *, field: str | None = None) -> TradeReviewWarning:
    return TradeReviewWarning(code=code, message=message, severity=ReviewWarningSeverity.WARNING, field=field)


def _error(code: str, message: str, *, field: str | None = None) -> TradeReviewWarning:
    return TradeReviewWarning(code=code, message=message, severity=ReviewWarningSeverity.ERROR, field=field)
