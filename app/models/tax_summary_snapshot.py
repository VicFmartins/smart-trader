from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum as SAEnum, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.trading_enums import AssetClass


def _enum_values(enum_cls) -> list[str]:
    return [item.value for item in enum_cls]


class TaxSummarySnapshot(Base):
    __tablename__ = "tax_summary_snapshots"
    __table_args__ = (
        UniqueConstraint("competence_month", "asset_class", "broker", name="uq_tax_summary_scope"),
        CheckConstraint("trade_count >= 0", name="ck_tax_summary_trade_count_non_negative"),
        CheckConstraint("total_fees >= 0", name="ck_tax_summary_total_fees_non_negative"),
        CheckConstraint("irrf_withheld >= 0", name="ck_tax_summary_irrf_non_negative"),
        CheckConstraint("carried_loss_balance >= 0", name="ck_tax_summary_loss_balance_non_negative"),
        CheckConstraint("estimated_tax_due >= 0", name="ck_tax_summary_estimated_tax_due_non_negative"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 1", name="ck_tax_summary_tax_rate_range"),
        Index("ix_tax_summary_month_asset_class", "competence_month", "asset_class"),
        Index("ix_tax_summary_broker_month", "broker", "competence_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    competence_month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    asset_class: Mapped[AssetClass | None] = mapped_column(
        SAEnum(
            AssetClass,
            name="tax_summary_asset_class",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=True,
        index=True,
    )
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gross_result: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False)
    total_fees: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False, default=Decimal("0.00"))
    net_result: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False)
    taxable_result: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False)
    irrf_withheld: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False, default=Decimal("0.00"))
    carried_loss_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False, default=Decimal("0.00"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4, asdecimal=True), nullable=False, default=Decimal("0.2000"))
    estimated_tax_due: Mapped[Decimal] = mapped_column(Numeric(18, 2, asdecimal=True), nullable=False, default=Decimal("0.00"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
