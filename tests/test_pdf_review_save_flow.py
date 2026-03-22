from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.import_job import ImportJob
from app.models.trade import Trade
from app.models.trading_enums import ImportJobStatus, TradeSourceType
from app.schemas.pdf_import import (
    BrokerDetectionResult,
    OllamaInferenceMetadata,
    PDFAssetClassification,
    PDFExtractionMetadata,
    PDFImportReviewPayload,
    PDFPageText,
    ReviewableTrade,
)
from app.services.auth import AuthService
from app.services.pdf_import.pipeline import PDFImportReviewService


def _build_client(tmp_path) -> tuple[TestClient, sessionmaker]:
    database_path = tmp_path / "pdf_review_save_flow.db"
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
    token = login_response.json()["data"]["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, SessionLocal


def test_pdf_review_to_bulk_save_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'pdf_review_save_flow.db'}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "pdf-review-save-secret")

    client, SessionLocal = _build_client(tmp_path)
    try:
        def stub_process_uploaded_stream(cls, filename, file_stream, import_batch_id=None):  # noqa: ANN001
            assert import_batch_id is not None
            return PDFImportReviewPayload(
                filename=filename,
                broker_detection=BrokerDetectionResult(
                    broker="XP",
                    confidence=0.98,
                    strategy="stub",
                    evidence=["xp investimentos"],
                ),
                normalized_broker="XP",
                normalized_trade_date=date(2026, 3, 20),
                extraction=PDFExtractionMetadata(
                    extractor_used="stub",
                    page_count=1,
                    extracted_characters=128,
                    text_truncated=False,
                ),
                llm=OllamaInferenceMetadata(
                    model="stub-model",
                    base_url="http://localhost:11434",
                    request_succeeded=True,
                    json_valid=True,
                    fallback_used=False,
                    raw_response='{"trades": 2}',
                ),
                pages=[PDFPageText(page_number=1, text="nota fake", char_count=9)],
                extracted_text="nota fake",
                trades=[
                    ReviewableTrade(
                        trade_index=0,
                        trade_date=date(2026, 3, 20),
                        trade_time="09:15:00",
                        asset_ticker="WINJ26",
                        asset_classification=PDFAssetClassification.WIN,
                        operation_type="buy",
                        quantity=2,
                        entry_price=Decimal("125000.00000"),
                        exit_price=Decimal("125100.00000"),
                        gross_result=Decimal("40.00"),
                        fees=Decimal("5.00"),
                        net_result=Decimal("35.00"),
                        broker="XP",
                        source_type=TradeSourceType.PDF_IMPORT,
                        imported_file_name=filename,
                        import_batch_id=import_batch_id,
                        notes="trade_time=09:15:00 | source_page=1",
                        confidence_score=0.94,
                        source_page=1,
                        ready_for_review=True,
                        ready_for_persistence=True,
                    ),
                    ReviewableTrade(
                        trade_index=1,
                        trade_date=date(2026, 3, 20),
                        trade_time="10:10:00",
                        asset_ticker="WDOJ26",
                        asset_classification=PDFAssetClassification.WDO,
                        operation_type="sell",
                        quantity=1,
                        entry_price=Decimal("5.72000"),
                        exit_price=Decimal("5.71000"),
                        gross_result=Decimal("0.10"),
                        fees=Decimal("0.00"),
                        net_result=Decimal("0.10"),
                        broker="XP",
                        source_type=TradeSourceType.PDF_IMPORT,
                        imported_file_name=filename,
                        import_batch_id=import_batch_id,
                        notes="trade_time=10:10:00 | source_page=1",
                        confidence_score=0.88,
                        source_page=1,
                        ready_for_review=True,
                        ready_for_persistence=True,
                    ),
                ],
                warnings=[],
                validation_errors=[],
                raw_json={"trades": 2},
                review_required=False,
            )

        monkeypatch.setattr(
            PDFImportReviewService,
            "process_uploaded_stream",
            classmethod(stub_process_uploaded_stream),
        )

        review_response = client.post(
            "/imports/pdf/review",
            files={"file": ("nota_xp.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

        assert review_response.status_code == 200
        review_payload = review_response.json()["data"]
        batch_id = review_payload["import_job"]["batch_id"]
        assert batch_id.startswith("pdf-")
        assert review_payload["trades"][0]["import_batch_id"] == batch_id

        bulk_response = client.post(
            "/trades/bulk",
            json={
                "trades": [
                    {
                        "trade_date": "2026-03-20",
                        "asset": "WIN",
                        "asset_class": "mini_index",
                        "operation_type": "buy",
                        "status": "closed",
                        "quantity": 2,
                        "entry_price": "125000.00000",
                        "exit_price": "125100.00000",
                        "gross_result": "40.00",
                        "fees": "5.00",
                        "net_result": "35.00",
                        "broker": "XP",
                        "source_type": "pdf_import",
                        "imported_file_name": "nota_xp.pdf",
                        "import_batch_id": batch_id,
                        "notes": "trade_time=09:15:00 | source_page=1",
                        "confidence_score": 0.94,
                    }
                ]
            },
        )

        assert bulk_response.status_code == 200
        bulk_payload = bulk_response.json()["data"]
        assert bulk_payload["created_count"] == 1
        assert bulk_payload["import_batch_id"] == batch_id
        assert bulk_payload["trades"][0]["imported_file_name"] == "nota_xp.pdf"
        assert bulk_payload["trades"][0]["import_batch_id"] == batch_id

        session: Session = SessionLocal()
        try:
            persisted_trades = list(session.scalars(select(Trade)).all())
            persisted_job = session.execute(select(ImportJob).where(ImportJob.batch_id == batch_id)).scalar_one()
        finally:
            session.close()

        assert len(persisted_trades) == 1
        assert persisted_trades[0].source_type == TradeSourceType.PDF_IMPORT
        assert persisted_trades[0].imported_file_name == "nota_xp.pdf"
        assert persisted_trades[0].import_batch_id == batch_id
        assert persisted_job.total_trades == 2
        assert persisted_job.imported_trades == 1
        assert persisted_job.rejected_trades == 1
        assert persisted_job.status == ImportJobStatus.PARTIAL
    finally:
        client.close()
