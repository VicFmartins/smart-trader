from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.models.trading_enums import AssetClass, OperationType, TradeAsset, TradeSourceType, TradeStatus
from app.schemas.common import ORMModel


class TradeResultFilter(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class TradeSortField(str, Enum):
    TRADE_DATE = "trade_date"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NET_RESULT = "net_result"
    GROSS_RESULT = "gross_result"
    ENTRY_PRICE = "entry_price"
    EXIT_PRICE = "exit_price"
    QUANTITY = "quantity"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class TradeBaseFields(BaseModel):
    trade_date: date
    asset: TradeAsset
    asset_class: AssetClass
    operation_type: OperationType
    status: TradeStatus = TradeStatus.CLOSED
    quantity: int = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    exit_price: Decimal | None = Field(default=None, gt=0)
    gross_result: Decimal | None = None
    fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    net_result: Decimal | None = None
    broker: str = Field(min_length=1, max_length=100)
    setup_id: int | None = Field(default=None, ge=1)
    source_type: TradeSourceType
    imported_file_name: str | None = Field(default=None, max_length=255)
    import_batch_id: str | None = Field(default=None, max_length=64)
    trade_time: time | None = None
    contract_code: str | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=4000)
    confidence_score: float | None = Field(default=None, ge=0, le=1)

    @field_validator("broker", "imported_file_name", "import_batch_id", "contract_code", "notes")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class TradeCreate(TradeBaseFields):
    pass


class TradeBulkCreate(BaseModel):
    trades: list[TradeCreate] = Field(min_length=1)


class TradeUpdate(BaseModel):
    trade_date: date | None = None
    asset: TradeAsset | None = None
    asset_class: AssetClass | None = None
    operation_type: OperationType | None = None
    status: TradeStatus | None = None
    quantity: int | None = Field(default=None, gt=0)
    entry_price: Decimal | None = Field(default=None, gt=0)
    exit_price: Decimal | None = Field(default=None, gt=0)
    gross_result: Decimal | None = None
    fees: Decimal | None = Field(default=None, ge=0)
    net_result: Decimal | None = None
    broker: str | None = Field(default=None, min_length=1, max_length=100)
    setup_id: int | None = Field(default=None, ge=1)
    source_type: TradeSourceType | None = None
    imported_file_name: str | None = Field(default=None, max_length=255)
    import_batch_id: str | None = Field(default=None, max_length=64)
    trade_time: time | None = None
    contract_code: str | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=4000)
    confidence_score: float | None = Field(default=None, ge=0, le=1)

    @field_validator("broker", "imported_file_name", "import_batch_id", "contract_code", "notes")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class TradeRead(ORMModel):
    id: int
    trade_date: date
    asset: TradeAsset
    asset_class: AssetClass
    operation_type: OperationType
    status: TradeStatus
    quantity: int
    entry_price: Decimal
    exit_price: Decimal | None
    gross_result: Decimal | None
    fees: Decimal
    net_result: Decimal | None
    broker: str
    setup_id: int | None
    source_type: TradeSourceType
    imported_file_name: str | None
    import_batch_id: str | None
    trade_time: time | None
    contract_code: str | None
    notes: str | None
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime


class TradeDeleteResponse(BaseModel):
    deleted: bool = True
    trade_id: int


class TradeBulkCreateResponse(BaseModel):
    created_count: int = Field(ge=0)
    import_batch_id: str | None = None
    trades: list[TradeRead] = Field(default_factory=list)


class TradeListParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    asset: TradeAsset | None = None
    broker: str | None = None
    setup_id: int | None = Field(default=None, ge=1)
    source_type: TradeSourceType | None = None
    status: TradeStatus | None = None
    result_filter: TradeResultFilter | None = None
    sort_by: TradeSortField = TradeSortField.TRADE_DATE
    sort_direction: SortDirection = SortDirection.DESC

    @field_validator("broker")
    @classmethod
    def normalize_broker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
