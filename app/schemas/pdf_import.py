from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.trading_enums import TradeSourceType
from app.schemas.import_job import ImportJobRead


def _normalize_optional_string(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


class PDFAssetClassification(str, Enum):
    WIN = "WIN"
    WDO = "WDO"
    OTHER = "OTHER"


class ReviewWarningSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class PDFPageText(BaseModel):
    page_number: int = Field(ge=1)
    text: str = ""
    char_count: int = Field(ge=0)


class BrokerDetectionResult(BaseModel):
    broker: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    strategy: str = "unknown"
    evidence: list[str] = Field(default_factory=list)

    @field_validator("broker", "strategy")
    @classmethod
    def normalize_strings(cls, value: object) -> str | None:
        return _normalize_optional_string(value)


class LLMTradeExtractionItem(BaseModel):
    trade_date: str | None = None
    asset: str | None = None
    asset_class: str | None = None
    operation_type: str | None = None
    quantity: int | float | str | None = None
    entry_price: Decimal | float | int | str | None = None
    exit_price: Decimal | float | int | str | None = None
    gross_result: Decimal | float | int | str | None = None
    fees: Decimal | float | int | str | None = None
    net_result: Decimal | float | int | str | None = None
    trade_time: str | None = None
    broker: str | None = None
    notes: str | None = None
    confidence_score: float | int | str | None = None
    source_page: int | float | str | None = None

    @field_validator("trade_date", "asset", "asset_class", "operation_type", "trade_time", "broker", "notes")
    @classmethod
    def normalize_optional_strings(cls, value: object) -> str | None:
        return _normalize_optional_string(value)


class LLMTradeExtractionPayload(BaseModel):
    broker: str | None = None
    document_date: str | None = None
    notes: str | None = None
    trades: list[LLMTradeExtractionItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("broker", "document_date", "notes")
    @classmethod
    def normalize_optional_strings(cls, value: object) -> str | None:
        return _normalize_optional_string(value)


class TradeReviewWarning(BaseModel):
    code: str
    message: str
    severity: ReviewWarningSeverity = ReviewWarningSeverity.WARNING
    field: str | None = None
    trade_index: int | None = Field(default=None, ge=0)

    @field_validator("code", "message", "field")
    @classmethod
    def normalize_strings(cls, value: object) -> str | None:
        return _normalize_optional_string(value)


class ReviewableTrade(BaseModel):
    trade_index: int = Field(ge=0)
    trade_date: date | None = None
    trade_time: str | None = None
    asset_ticker: str | None = None
    asset_classification: PDFAssetClassification = PDFAssetClassification.OTHER
    operation_type: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    entry_price: Decimal | None = Field(default=None, gt=0)
    exit_price: Decimal | None = Field(default=None, gt=0)
    gross_result: Decimal | None = None
    fees: Decimal | None = Field(default=None, ge=0)
    net_result: Decimal | None = None
    broker: str | None = None
    setup_id: int | None = None
    source_type: TradeSourceType = TradeSourceType.PDF_IMPORT
    imported_file_name: str
    import_batch_id: str | None = None
    notes: str | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    source_page: int | None = Field(default=None, ge=1)
    warnings: list[TradeReviewWarning] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    ready_for_review: bool = True
    ready_for_persistence: bool = False

    @field_validator("trade_time", "asset_ticker", "operation_type", "broker", "imported_file_name", "import_batch_id", "notes")
    @classmethod
    def normalize_optional_strings(cls, value: object) -> str | None:
        return _normalize_optional_string(value)


class PDFExtractionMetadata(BaseModel):
    extractor_used: str
    page_count: int = Field(ge=0)
    extracted_characters: int = Field(ge=0)
    text_truncated: bool = False


class OllamaInferenceMetadata(BaseModel):
    model: str
    base_url: str
    request_succeeded: bool = False
    json_valid: bool = False
    fallback_used: bool = False
    raw_response: str | None = None

    @field_validator("model", "base_url", "raw_response")
    @classmethod
    def normalize_strings(cls, value: object) -> str | None:
        return _normalize_optional_string(value)


class PDFImportReviewPayload(BaseModel):
    filename: str
    import_job: ImportJobRead | None = None
    broker_detection: BrokerDetectionResult
    normalized_broker: str | None = None
    normalized_trade_date: date | None = None
    extraction: PDFExtractionMetadata
    llm: OllamaInferenceMetadata
    pages: list[PDFPageText] = Field(default_factory=list)
    extracted_text: str = ""
    trades: list[ReviewableTrade] = Field(default_factory=list)
    warnings: list[TradeReviewWarning] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    raw_json: dict[str, Any] | list[Any] | None = None
    review_required: bool = True

    @field_validator("filename")
    @classmethod
    def normalize_filename(cls, value: object) -> str:
        cleaned = _normalize_optional_string(value)
        if cleaned is None:
            raise ValueError("filename is required.")
        return cleaned

    @field_validator("normalized_broker")
    @classmethod
    def normalize_broker(cls, value: object) -> str | None:
        return _normalize_optional_string(value)
