from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("client_id", "broker", name="uq_account_client_broker"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    broker: Mapped[str] = mapped_column(String(100), nullable=False)

    client: Mapped["Client"] = relationship(back_populates="accounts")
    positions: Mapped[list["PositionHistory"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )
