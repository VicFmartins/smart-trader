from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PositionHistory(Base):
    __tablename__ = "positions_history"
    __table_args__ = (
        UniqueConstraint("account_id", "asset_id", "reference_date", name="uq_position_snapshot"),
        CheckConstraint("quantity >= 0", name="ck_positions_history_quantity_non_negative"),
        CheckConstraint("avg_price >= 0", name="ck_positions_history_avg_price_non_negative"),
        CheckConstraint("total_value >= 0", name="ck_positions_history_total_value_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets_master.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8, asdecimal=True), nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(24, 8, asdecimal=True), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(24, 8, asdecimal=True), nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    account: Mapped["Account"] = relationship(back_populates="positions")
    asset: Mapped["AssetMaster"] = relationship(back_populates="positions")
