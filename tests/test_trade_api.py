from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.setup import Setup
from app.schemas.auth import TokenResponse
from app.services.auth import AuthService


def _build_client(tmp_path) -> tuple[TestClient, sessionmaker]:
    database_path = tmp_path / "trade_api_test.db"
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
        session.add(Setup(name="Abertura 9h", asset_class_scope="mini_index"))
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


def test_trade_crud_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'trade_api_test.db'}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")

    client, SessionLocal = _build_client(tmp_path)
    try:
        setup_session = SessionLocal()
        try:
            setup_id = setup_session.query(Setup).filter(Setup.name == "Abertura 9h").one().id
        finally:
            setup_session.close()

        create_response = client.post(
            "/trades",
            json={
                "trade_date": "2026-03-20",
                "asset": "WIN",
                "asset_class": "mini_index",
                "operation_type": "buy",
                "status": "closed",
                "quantity": 2,
                "entry_price": "125000.0",
                "exit_price": "125100.0",
                "fees": "5.00",
                "broker": "xp",
                "setup_id": setup_id,
                "source_type": "manual",
            },
        )

        assert create_response.status_code == 200
        trade_payload = create_response.json()["data"]
        assert trade_payload["gross_result"] == "40.00"
        assert trade_payload["net_result"] == "35.00"
        assert trade_payload["broker"] == "XP"
        trade_id = trade_payload["id"]

        draft_response = client.post(
            "/trades",
            json={
                "trade_date": "2026-03-21",
                "asset": "WDO",
                "asset_class": "mini_dollar",
                "operation_type": "sell",
                "status": "draft",
                "quantity": 1,
                "entry_price": "5.7200",
                "fees": "0.00",
                "broker": "clear",
                "source_type": "manual",
            },
        )

        assert draft_response.status_code == 200
        assert draft_response.json()["data"]["exit_price"] is None
        assert draft_response.json()["data"]["gross_result"] is None

        list_response = client.get(
            "/trades",
            params={"asset": "WIN", "result_filter": "positive", "sort_by": "net_result", "sort_direction": "desc"},
        )

        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert list_payload["pagination"]["total"] == 1
        assert list_payload["data"][0]["id"] == trade_id

        update_response = client.patch(
            f"/trades/{trade_id}",
            json={
                "exit_price": "125080.0",
                "fees": "8.00",
            },
        )

        assert update_response.status_code == 200
        updated_payload = update_response.json()["data"]
        assert updated_payload["gross_result"] == "32.00"
        assert updated_payload["net_result"] == "24.00"

        close_draft_response = client.patch(
            f"/trades/{draft_response.json()['data']['id']}",
            json={
                "status": "closed",
                "exit_price": "5.7100",
            },
        )

        assert close_draft_response.status_code == 200
        closed_payload = close_draft_response.json()["data"]
        assert closed_payload["gross_result"] == "0.10"
        assert closed_payload["net_result"] == "0.10"

        delete_response = client.delete(f"/trades/{trade_id}")

        assert delete_response.status_code == 200
        assert delete_response.json()["data"] == {"deleted": True, "trade_id": trade_id}

        missing_response = client.get(f"/trades/{trade_id}")
        assert missing_response.status_code == 404
    finally:
        client.close()
