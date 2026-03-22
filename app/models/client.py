from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    risk_profile: Mapped[str] = mapped_column(String(50), nullable=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="client", cascade="all, delete-orphan")
