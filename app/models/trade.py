from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, Numeric, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.trading_enums import AssetClass, OperationType, TradeAsset, TradeSourceType, TradeStatus


def _enum_values(enum_cls) -> list[str]:
    return [item.value for item in enum_cls]


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_trades_quantity_positive"),
        CheckConstraint("entry_price > 0", name="ck_trades_entry_price_positive"),
        CheckConstraint("exit_price IS NULL OR exit_price > 0", name="ck_trades_exit_price_positive"),
        CheckConstraint("fees >= 0", name="ck_trades_fees_non_negative"),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_trades_confidence_score_range",
        ),
        CheckConstraint(
            "(status != 'closed') OR (exit_price IS NOT NULL AND gross_result IS NOT NULL AND net_result IS NOT NULL)",
            name="ck_trades_closed_fields_required",
        ),
        CheckConstraint(
            "(source_type != 'pdf_import') OR imported_file_name IS NOT NULL",
            name="ck_trades_imported_file_required_for_pdf",
        ),
        CheckConstraint(
            "(source_type != 'pdf_import') OR import_batch_id IS NOT NULL",
            name="ck_trades_import_batch_required_for_pdf",
        ),
        CheckConstraint(
            "(asset = 'WIN' AND asset_class = 'mini_index') OR (asset = 'WDO' AND asset_class = 'mini_dollar')",
            name="ck_trades_asset_matches_class",
        ),
        Index("ix_trades_trade_date_asset", "trade_date", "asset"),
        Index("ix_trades_asset_class_trade_date", "asset_class", "trade_date"),
        Index("ix_trades_broker_trade_date", "broker", "trade_date"),
        Index("ix_trades_status_trade_date", "status", "trade_date"),
        Index("ix_trades_setup_trade_date", "setup_id", "trade_date"),
        Index("ix_trades_import_batch_trade_date", "import_batch_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    asset: Mapped[TradeAsset] = mapped_column(
        SAEnum(TradeAsset, name="trade_asset", native_enum=False, validate_strings=True, values_callable=_enum_values),
        nullable=False,
        index=True,
    )
    asset_class: Mapped[AssetClass] = mapped_column(
        SAEnum(AssetClass, name="trade_asset_class", native_enum=False, validate_strings=True, values_callable=_enum_values),
        nullable=False,
        index=True,
    )
    operation_type: Mapped[OperationType] = mapped_column(
        SAEnum(
            OperationType,
            name="trade_operation_type",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[TradeStatus] = mapped_column(
        SAEnum(TradeStatus, name="trade_status", native_enum=False, validate_strings=True, values_callable=_enum_values),
        nullable=False,
        default=TradeStatus.CLOSED,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 5, asdecimal=True), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 5, asdecimal=True), nullable=True)
    gross_result: Mapped[Decimal | None] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False, default=Decimal("0.00"))
    net_result: Mapped[Decimal | None] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=True)
    broker: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    setup_id: Mapped[int | None] = mapped_column(ForeignKey("setups.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type: Mapped[TradeSourceType] = mapped_column(
        SAEnum(
            TradeSourceType,
            name="trade_source_type",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    imported_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    import_batch_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("import_jobs.batch_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trade_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    contract_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    setup: Mapped["Setup | None"] = relationship(back_populates="trades")
    import_job: Mapped["ImportJob | None"] = relationship(back_populates="trades")
