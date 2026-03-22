from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.trading_enums import AssetClass


def _enum_values(enum_cls) -> list[str]:
    return [item.value for item in enum_cls]


class Setup(Base):
    __tablename__ = "setups"
    __table_args__ = (
        UniqueConstraint("name", name="uq_setups_name"),
        Index("ix_setups_active_asset_scope", "is_active", "asset_class_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_class_scope: Mapped[AssetClass | None] = mapped_column(
        SAEnum(
            AssetClass,
            name="setup_asset_class_scope",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    trades: Mapped[list["Trade"]] = relationship(back_populates="setup")
