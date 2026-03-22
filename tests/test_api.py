from __future__ import annotations

import io
from datetime import date
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.account import Account
from app.models.accepted_column_mapping import AcceptedColumnMapping
from app.models.asset_master import AssetMaster
from app.models.client import Client
from app.models.ingestion_report import IngestionReport
from app.models.position_history import PositionHistory
from app.models.user import User
from app.api.routes import upload as upload_route_module
from app.etl.detect.column_mapper import FuzzyColumnMapper
from app.etl.extract.file_reader import FileReader
from app.schemas.etl import UploadResponse
from app.services.accepted_mapping_service import AcceptedMappingService
from app.services.auth_service import AuthService
from app.services.etl_service import ETLService


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    database_path = tmp_path / "api_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")

    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session: Session = TestingSessionLocal()
    try:
        AuthService(session).create_user(
            email="admin@carteira.local",
            password="super-secret",
            full_name="Admin Local",
            is_admin=True,
        )
        client_1 = Client(name="Ana Costa", risk_profile="arrojado")
        client_2 = Client(name="Maria Oliveira", risk_profile="moderado")
        session.add_all([client_1, client_2])
        session.flush()

        account_1 = Account(client_id=client_1.id, broker="XP")
        account_2 = Account(client_id=client_2.id, broker="BTG")
        session.add_all([account_1, account_2])
        session.flush()

        asset_1 = AssetMaster(
            ticker="PETR4",
            original_name="PETR4",
            normalized_name="PETR4",
            asset_class="equities",
            cnpj="00.000.000/0001-00",
            maturity_date=None,
        )
        asset_2 = AssetMaster(
            ticker="BTC",
            original_name="Bitcoin",
            normalized_name="BITCOIN",
            asset_class="crypto",
            cnpj=None,
            maturity_date=None,
        )
        session.add_all([asset_1, asset_2])
        session.flush()

        session.add_all(
            [
                PositionHistory(
                    account_id=account_1.id,
                    asset_id=asset_1.id,
                    quantity=Decimal("10"),
                    avg_price=Decimal("30"),
                    total_value=Decimal("300"),
                    reference_date=date(2026, 3, 15),
                ),
                PositionHistory(
                    account_id=account_2.id,
                    asset_id=asset_2.id,
                    quantity=Decimal("0.1"),
                    avg_price=Decimal("500000"),
                    total_value=Decimal("50000"),
                    reference_date=date(2026, 3, 16),
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    app = create_app()
    app.state.testing_session_factory = TestingSessionLocal

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@carteira.local", "password": "super-secret"},
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def unauthenticated_api_client(tmp_path, monkeypatch):
    database_path = tmp_path / "api_public_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")

    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session: Session = TestingSessionLocal()
    try:
        AuthService(session).create_user(
            email="admin@carteira.local",
            password="super-secret",
            full_name="Admin Local",
            is_admin=True,
        )
        session.commit()
    finally:
        session.close()

    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_login_returns_a_jwt_and_me_returns_the_authenticated_user(unauthenticated_api_client: TestClient) -> None:
    login_response = unauthenticated_api_client.post(
        "/auth/login",
        json={"email": "admin@carteira.local", "password": "super-secret"},
    )

    assert login_response.status_code == 200
    payload = login_response.json()["data"]
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["email"] == "admin@carteira.local"

    me_response = unauthenticated_api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert me_response.status_code == 200
    me_payload = me_response.json()["data"]
    assert me_payload["email"] == "admin@carteira.local"
    assert me_payload["is_admin"] is True


def test_protected_routes_require_authentication(unauthenticated_api_client: TestClient) -> None:
    response = unauthenticated_api_client.get("/clients")

    assert response.status_code == 401
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "authentication_error"


def test_clients_endpoint_supports_pagination_and_filtering(api_client: TestClient) -> None:
    response = api_client.get("/clients", params={"risk_profile": "moderado", "limit": 1, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["pagination"] == {
        "total": 1,
        "offset": 0,
        "limit": 1,
        "count": 1,
        "has_more": False,
    }
    assert payload["data"][0]["name"] == "Maria Oliveira"


def test_assets_endpoint_supports_search(api_client: TestClient) -> None:
    response = api_client.get("/assets", params={"search": "bit"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["data"][0]["asset_class"] == "crypto"


def test_positions_endpoint_returns_validation_errors_in_standard_format(api_client: TestClient) -> None:
    response = api_client.get("/positions", params={"limit": 0})

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "request_validation_error"
    assert payload["errors"][0]["field"] == "limit"


def test_portfolio_pdf_report_endpoint_returns_a_pdf(api_client: TestClient) -> None:
    response = api_client.get("/reports/portfolio/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment;" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content.startswith(b"%PDF")


def test_upload_endpoint_processes_a_supported_file(api_client: TestClient) -> None:
    csv_content = "\n".join(
        [
            "cliente,perfil,corretora,ativo,ticker,quantidade,preco medio,valor total,data referencia",
            "Carlos Lima,moderado,XP,Tesouro Selic 2029,SELIC29,2,10100.50,20201.00,2026-03-17",
        ]
    ).encode("utf-8")

    response = api_client.post(
        "/upload",
        files={"file": ("carteira.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["filename"] == "carteira.csv"
    assert payload["data"]["detected_type"] == "csv"
    assert payload["data"]["rows_processed"] == 1
    assert payload["data"]["ingestion_report_id"] is not None
    assert payload["data"]["processed_at"]
    datetime.fromisoformat(payload["data"]["processed_at"])

    positions_response = api_client.get("/positions")
    assert positions_response.status_code == 200
    assert positions_response.json()["pagination"]["total"] == 3

    reports_response = api_client.get("/ingestion-reports")
    reports_payload = reports_response.json()
    assert reports_response.status_code == 200
    assert reports_payload["pagination"]["total"] == 1
    assert reports_payload["data"][0]["id"] == payload["data"]["ingestion_report_id"]
    assert reports_payload["data"][0]["status"] == "success"
    assert reports_payload["data"][0]["review_status"] == "not_required"

    Path(payload["data"]["raw_file"]).unlink(missing_ok=True)
    Path(payload["data"]["processed_file"]).unlink(missing_ok=True)


def test_upload_endpoint_rejects_unsupported_extension(api_client: TestClient) -> None:
    response = api_client.post(
        "/upload",
        files={"file": ("notas.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "etl_input_error"


def test_upload_endpoint_materializes_file_before_executor(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_process_uploaded_stream(filename: str, file_stream: io.BytesIO) -> UploadResponse:
        captured["filename"] = filename
        captured["stream_type"] = type(file_stream)
        captured["content"] = file_stream.read()
        return UploadResponse(
            filename=filename,
            detected_type="csv",
            rows_processed=1,
            rows_skipped=0,
            message="ok",
            processed_at=datetime.now().isoformat(),
            raw_file="data/raw/upload.csv",
            processed_file="data/processed/normalized.csv",
        )

    monkeypatch.setattr(ETLService, "process_uploaded_stream", fake_process_uploaded_stream)

    response = api_client.post(
        "/upload",
        files={"file": ("carteira.csv", b"coluna\nvalor\n", "text/csv")},
    )

    assert response.status_code == 200
    assert captured["filename"] == "carteira.csv"
    assert captured["stream_type"] is io.BytesIO
    assert captured["content"] == b"coluna\nvalor\n"


def test_upload_endpoint_rejects_payloads_larger_than_limit(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(upload_route_module, "MAX_UPLOAD_SIZE_BYTES", 8)

    response = api_client.post(
        "/upload",
        files={"file": ("carteira.csv", b"123456789", "text/csv")},
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "upload_too_large"


def test_upload_persists_review_required_ingestion_report(api_client: TestClient) -> None:
    csv_content = "\n".join(
        [
            "cliente,corretora,ativo,quantidade",
            "Carlos Lima,XP,Tesouro Selic 2029,2",
        ]
    ).encode("utf-8")

    response = api_client.post(
        "/upload",
        files={"file": ("carteira_incompleta.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["review_required"] is True
    assert any("reference_date" in reason for reason in payload["review_reasons"])

    reports_response = api_client.get("/ingestion-reports", params={"review_required": "true"})
    reports_payload = reports_response.json()
    assert reports_response.status_code == 200
    assert reports_payload["pagination"]["total"] == 1
    report = reports_payload["data"][0]
    assert report["id"] == payload["ingestion_report_id"]
    assert report["review_required"] is True
    assert report["status"] == "review_required"
    assert report["review_status"] == "pending"
    assert "cliente" in [column.lower() for column in report["detected_columns"]]


def test_upload_infers_missing_broker_from_filename_and_keeps_processing(api_client: TestClient) -> None:
    csv_content = "\n".join(
        [
            "cliente,advisorcode,ativo,quantidade,data referencia",
            "Carlos Lima,XP-001,Tesouro Selic 2029,2,2026-03-17",
        ]
    ).encode("utf-8")

    response = api_client.post(
        "/upload",
        files={"file": ("XP_leads_positions.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["rows_processed"] == 1
    assert payload["review_required"] is True
    assert "broker_inferred" in payload["review_reasons"]

    reports_response = api_client.get(f"/ingestion-reports/{payload['ingestion_report_id']}")
    report = reports_response.json()["data"]
    assert report["status"] == "review_required"
    assert report["review_status"] == "pending"
    assert "advisorcode" in [column.lower() for column in report["detected_columns"]]


def test_get_ingestion_report_returns_report_details(api_client: TestClient) -> None:
    csv_content = "\n".join(
        [
            "cliente,corretora,ativo,quantidade,data referencia",
            "Carlos Lima,XP,Tesouro Selic 2029,2,2026-03-17",
        ]
    ).encode("utf-8")

    upload_response = api_client.post(
        "/upload",
        files={"file": ("carteira_detalhe.csv", csv_content, "text/csv")},
    )
    report_id = upload_response.json()["data"]["ingestion_report_id"]

    response = api_client.get(f"/ingestion-reports/{report_id}")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == report_id
    assert payload["filename"] == "carteira_detalhe.csv"
    assert payload["status"] == "success"
    assert payload["parser_name"] in {"smart_tabular_reader", "generic_csv_reader"}


def test_ingestion_report_review_approval_persists_accepted_mappings_and_reuses_them(
    api_client: TestClient,
    tmp_path: Path,
) -> None:
    csv_content = "\n".join(
        [
            "Cliente do Investidor;Instituição Financeira;Papel / Ativo;Qtde Total",
            "Carlos Lima;XP Investimentos;Tesouro Selic 2029;2",
        ]
    ).encode("utf-8")

    upload_response = api_client.post(
        "/upload",
        files={"file": ("layout_para_review.csv", csv_content, "text/csv")},
    )
    report_id = upload_response.json()["data"]["ingestion_report_id"]

    review_response = api_client.patch(
        f"/ingestion-reports/{report_id}/review",
        json={"review_status": "approved", "approved_by": "ops@carteira.local"},
    )

    assert review_response.status_code == 200
    reviewed_report = review_response.json()["data"]
    assert reviewed_report["review_status"] == "approved"
    assert reviewed_report["review_required"] is False

    session = api_client.app.state.testing_session_factory()
    try:
        mappings = session.query(AcceptedColumnMapping).all()
        assert len(mappings) >= 4
        layout_signature = reviewed_report["layout_signature"]
        preferred_mappings = AcceptedMappingService(session).get_preferred_mappings(layout_signature=layout_signature)
        assert preferred_mappings["cliente do investidor"] == "client_name"

        file_reader = FileReader(
            mapping_resolver=lambda signature: AcceptedMappingService(session).get_preferred_mappings(layout_signature=signature),
            mapper=FuzzyColumnMapper(threshold=101.0),
        )
        tmp_file = tmp_path / "reuse_layout.csv"
        tmp_file.write_text(
            "\n".join(
                [
                    "Cliente do Investidor;Instituição Financeira;Papel / Ativo;Qtde Total",
                    "Carlos Lima;XP Investimentos;Tesouro Selic 2029;2",
                ]
            ),
            encoding="utf-8",
        )
        dataframe = file_reader.read(tmp_file)
        assert dataframe.attrs["column_mapping"][0]["matched_alias"] == "accepted_mapping"
        assert "client_name" in dataframe.columns
        assert "asset_name" in dataframe.columns
        assert "quantity" in dataframe.columns
        assert dataframe.loc[0, "client_name"] == "Carlos Lima"
        tmp_file.unlink(missing_ok=True)
    finally:
        session.close()


def test_ingestion_reports_support_review_status_filter(api_client: TestClient) -> None:
    csv_content = "\n".join(
        [
            "cliente,corretora,ativo,quantidade",
            "Carlos Lima,XP,Tesouro Selic 2029,2",
        ]
    ).encode("utf-8")
    api_client.post("/upload", files={"file": ("pendente.csv", csv_content, "text/csv")})

    response = api_client.get("/ingestion-reports", params={"review_status": "pending"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["data"][0]["review_status"] == "pending"


def test_reprocess_endpoint_rejects_pending_report(api_client: TestClient) -> None:
    csv_content = "\n".join(
        [
            "Cliente do Investidor;Instituicao Financeira;Papel / Ativo;Qtde Total",
            "Carlos Lima;XP Investimentos;Tesouro Selic 2029;2",
        ]
    ).encode("utf-8")

    upload_response = api_client.post(
        "/upload",
        files={"file": ("pendente_reprocesso.csv", csv_content, "text/csv")},
    )
    report_id = upload_response.json()["data"]["ingestion_report_id"]

    response = api_client.post(f"/ingestion-reports/{report_id}/reprocess")

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "etl_input_error"


def test_error_report_cannot_be_approved(api_client: TestClient) -> None:
    session = api_client.app.state.testing_session_factory()
    try:
        report = IngestionReport(
            filename="falha.xlsx",
            source_file="/tmp/falha.xlsx",
            source_type="local",
            detected_type="excel",
            review_required=True,
            review_status="pending",
            review_reasons=["processing_failed"],
            detected_columns=[],
            applied_mappings=[],
            structure_detection={},
            rows_processed=0,
            rows_skipped=0,
            status="error",
            message="Falha tecnica",
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        report_id = report.id
    finally:
        session.close()

    response = api_client.patch(
        f"/ingestion-reports/{report_id}/review",
        json={"review_status": "approved"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "etl_input_error"


def test_approved_report_can_be_reprocessed_in_place(api_client: TestClient) -> None:
    csv_content = "\n".join(
        [
            "Cliente do Investidor;Instituicao Financeira;Papel / Ativo;Qtde Total",
            "Carlos Lima;XP Investimentos;Tesouro Selic 2029;2",
        ]
    ).encode("utf-8")

    upload_response = api_client.post(
        "/upload",
        files={"file": ("reprocessar_layout.csv", csv_content, "text/csv")},
    )
    report_id = upload_response.json()["data"]["ingestion_report_id"]

    review_response = api_client.patch(
        f"/ingestion-reports/{report_id}/review",
        json={"review_status": "approved", "approved_by": "ops@carteira.local"},
    )
    assert review_response.status_code == 200

    reprocess_response = api_client.post(f"/ingestion-reports/{report_id}/reprocess")

    assert reprocess_response.status_code == 200
    payload = reprocess_response.json()["data"]
    assert payload["ingestion_report_id"] == report_id
    assert payload["reprocess_count"] == 1
    assert payload["reprocessed_at"] is not None

    detail_response = api_client.get(f"/ingestion-reports/{report_id}")
    detail_payload = detail_response.json()["data"]
    assert detail_payload["id"] == report_id
    assert detail_payload["reprocess_count"] == 1
    assert detail_payload["reprocessed_at"] is not None
    assert detail_payload["review_status"] == "pending"
    assert any(
        mapping.get("matched_alias") == "accepted_mapping"
        for mapping in detail_payload["applied_mappings"]
        if mapping.get("accepted")
    )
