from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssetMaster(Base):
    __tablename__ = "assets_master"
    __table_args__ = (
        UniqueConstraint("ticker", name="uq_assets_master_ticker"),
        UniqueConstraint("normalized_name", "asset_class", name="uq_assets_master_normalized_class"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cnpj: Mapped[str | None] = mapped_column(String(18), nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    positions: Mapped[list["PositionHistory"]] = relationship(back_populates="asset")
