from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.setup import Setup
from app.models.trade import Trade
from app.models.trading_enums import AssetClass, OperationType, TradeAsset, TradeSourceType, TradeStatus
from app.schemas.auth import TokenResponse
from app.services.auth import AuthService


def _build_client(tmp_path) -> tuple[TestClient, sessionmaker]:
    database_path = tmp_path / "trade_analytics_api.db"
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session: Session = SessionLocal()
    try:
        AuthService(session).create_user(
            email="admin@smarttrade.local",
            password="super-secret",
            full_name="Admin Local",
            is_admin=True,
        )
        setup = Setup(name="Abertura", asset_class_scope=AssetClass.MINI_INDEX)
        session.add(setup)
        session.flush()
        session.add_all(
            [
                Trade(
                    trade_date=date(2026, 3, 20),
                    asset=TradeAsset.WIN,
                    asset_class=AssetClass.MINI_INDEX,
                    operation_type=OperationType.BUY,
                    status=TradeStatus.CLOSED,
                    quantity=2,
                    entry_price=Decimal("125000.0"),
                    exit_price=Decimal("125100.0"),
                    gross_result=Decimal("40.00"),
                    fees=Decimal("5.00"),
                    net_result=Decimal("35.00"),
                    broker="XP",
                    setup_id=setup.id,
                    source_type=TradeSourceType.MANUAL,
                    created_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
                ),
                Trade(
                    trade_date=date(2026, 3, 21),
                    asset=TradeAsset.WDO,
                    asset_class=AssetClass.MINI_DOLLAR,
                    operation_type=OperationType.SELL,
                    status=TradeStatus.CLOSED,
                    quantity=1,
                    entry_price=Decimal("5.7200"),
                    exit_price=Decimal("5.7300"),
                    gross_result=Decimal("-0.10"),
                    fees=Decimal("0.00"),
                    net_result=Decimal("-0.10"),
                    broker="CLEAR",
                    source_type=TradeSourceType.PDF_IMPORT,
                    imported_file_name="batch.pdf",
                    import_batch_id="batch-1",
                    confidence_score=0.88,
                    created_at=datetime(2026, 3, 21, 10, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 21, 10, 0, tzinfo=UTC),
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    app = create_app()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    login_response = client.post("/auth/login", json={"email": "admin@smarttrade.local", "password": "super-secret"})
    token = TokenResponse(**login_response.json()["data"]).access_token
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, SessionLocal


def test_trade_analytics_endpoint_returns_snapshot_with_filters(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'trade_analytics_api.db'}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")

    client, _ = _build_client(tmp_path)
    try:
        response = client.get("/analytics/trades", params={"asset": "WIN", "broker": "xp"})

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["summary"]["total_trades"] == 1
        assert payload["summary"]["net_pnl"] == 35.0
        assert payload["pnl_by_asset"][0]["label"] == "WIN"
        assert payload["pnl_by_setup"][0]["label"] == "Abertura"
    finally:
        client.close()
