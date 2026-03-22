from __future__ import annotations

from enum import Enum


class TradeAsset(str, Enum):
    WIN = "WIN"
    WDO = "WDO"


class AssetClass(str, Enum):
    MINI_INDEX = "mini_index"
    MINI_DOLLAR = "mini_dollar"


class OperationType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeSourceType(str, Enum):
    MANUAL = "manual"
    PDF_IMPORT = "pdf_import"


class TradeStatus(str, Enum):
    DRAFT = "draft"
    CLOSED = "closed"


class ImportJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
