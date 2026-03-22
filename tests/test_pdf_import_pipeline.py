from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.api.routes import pdf_imports as pdf_import_route_module
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.trading_enums import AssetClass, OperationType, TradeAsset, TradeSourceType
from app.schemas.pdf_import import (
    BrokerDetectionResult,
    LLMTradeExtractionPayload,
    OllamaInferenceMetadata,
    PDFAssetClassification,
    PDFExtractionMetadata,
    PDFImportReviewPayload,
    PDFPageText,
    TradeReviewWarning,
)
from app.services.auth_service import AuthService
from app.services.pdf_import.extraction import PDFExtractionResult
from app.services.pdf_import.json_parser import ParsedStructuredOutput, StructuredOutputParser
from app.services.pdf_import.ollama_client import OllamaChatResult
from app.services.pdf_import.parsers import BrokerParserContext, GenericOllamaBrokerParser
from app.services.pdf_import.pipeline import PDFImportReviewService
from app.services.pdf_import.validation import TradeExtractionNormalizer


def test_structured_output_parser_recovers_json_from_markdown_fence() -> None:
    raw_response = """
    The extracted payload is below.
    ```json
    {
      "broker": "XP",
      "document_date": "2026-03-20",
      "notes": null,
      "trades": [
        {
          "trade_date": "2026-03-20",
          "asset": "WIN",
          "asset_class": "mini_index",
          "operation_type": "buy",
          "quantity": 2,
          "entry_price": 125000.0,
          "exit_price": 125150.0,
          "gross_result": 60.0,
          "fees": 5.0,
          "net_result": 55.0,
          "broker": "XP",
          "notes": null,
          "confidence_score": 0.91,
          "source_page": 1
        }
      ],
      "warnings": []
    }
    ```
    """

    parsed = StructuredOutputParser().parse(raw_response, LLMTradeExtractionPayload)

    assert parsed.is_valid is True
    assert parsed.payload is not None
    assert parsed.payload.broker == "XP"
    assert parsed.payload.trades[0].asset == "WIN"
    assert parsed.payload.trades[0].asset_class == "mini_index"
    assert parsed.warnings == ["Structured output required fallback JSON recovery."]


def test_generic_ollama_parser_repairs_invalid_json() -> None:
    class FakeOllamaClient:
        def __init__(self) -> None:
            self.repair_called = False

        def chat_with_schema(self, *, prompt: str, schema: dict, model: str | None = None) -> OllamaChatResult:
            return OllamaChatResult(model="local-model", content="{broker: XP, trades: [}", response_json={})

        def repair_json(self, *, invalid_response: str, schema: dict, model: str | None = None) -> OllamaChatResult:
            self.repair_called = True
            return OllamaChatResult(
                model="local-model",
                content=(
                    '{"broker":"CLEAR","document_date":"2026-03-21","notes":null,'
                    '"trades":[{"trade_date":"2026-03-21","asset":"WDO","asset_class":"mini_dollar",'
                    '"operation_type":"sell","quantity":1,"entry_price":5.72,"exit_price":5.71,'
                    '"gross_result":100.0,"fees":5.0,"net_result":95.0,"broker":"CLEAR",'
                    '"notes":null,"confidence_score":0.87,"source_page":2}],"warnings":[]}'
                ),
                response_json={},
            )

    fake_client = FakeOllamaClient()
    parser = GenericOllamaBrokerParser(ollama_client=fake_client, output_parser=StructuredOutputParser())

    response, parsed, fallback_used = parser.parse(
        BrokerParserContext(
            filename="nota_clear.pdf",
            extracted_text="CLEAR CORRETORA\nWIN/WDO day trade note",
            broker_detection=BrokerDetectionResult(broker="CLEAR", confidence=0.9, strategy="text", evidence=["clear corretora"]),
        )
    )

    assert fallback_used is True
    assert fake_client.repair_called is True
    assert response.model == "local-model"
    assert parsed.is_valid is True
    assert parsed.payload is not None
    assert parsed.payload.trades[0].asset == "WDO"
    assert parsed.payload.trades[0].operation_type == "sell"


def test_pdf_import_review_service_returns_reviewable_payload() -> None:
    class StubExtractor:
        def extract(self, file_bytes: bytes) -> PDFExtractionResult:
            return PDFExtractionResult(
                pages=[PDFPageText(page_number=1, text="XP INVESTIMENTOS\nNOTA DE CORRETAGEM", char_count=31)],
                combined_text="XP INVESTIMENTOS\nNOTA DE CORRETAGEM",
                metadata=PDFExtractionMetadata(
                    extractor_used="stub",
                    page_count=1,
                    extracted_characters=31,
                    text_truncated=False,
                ),
            )

    class StubParser:
        def parse(self, context: BrokerParserContext):
            payload = LLMTradeExtractionPayload.model_validate(
                {
                    "broker": "XP",
                    "document_date": "2026-03-20",
                    "notes": None,
                    "trades": [
                        {
                            "trade_date": "2026-03-20",
                            "asset": "WIN",
                            "asset_class": "WIN",
                            "operation_type": "buy",
                            "quantity": 1,
                            "entry_price": "125000.0",
                            "exit_price": "125100.0",
                            "gross_result": "20.00",
                            "fees": "3.00",
                            "net_result": "17.00",
                            "trade_time": "09:15:00",
                            "broker": None,
                            "notes": "Morning breakout",
                            "confidence_score": 0.93,
                            "source_page": 1,
                        }
                    ],
                    "warnings": [],
                }
            )
            return (
                OllamaChatResult(model="stub-model", content='{"ok": true}', response_json={}),
                ParsedStructuredOutput(
                    payload=payload,
                    raw_json={"broker": "XP"},
                    warnings=[],
                    errors=[],
                    cleaned_json_text='{"broker":"XP"}',
                ),
                False,
            )

    class StubRegistry:
        def resolve(self, broker: str | None):
            return StubParser()

    class StubOllamaClient:
        base_url = "http://localhost:11434"

    service = PDFImportReviewService(
        text_extractor=StubExtractor(),
        broker_detector=type(
            "StubBrokerDetector",
            (),
            {
                "detect": lambda self, *, filename, extracted_text: BrokerDetectionResult(
                    broker="XP",
                    confidence=0.95,
                    strategy="text",
                    evidence=["xp investimentos"],
                )
            },
        )(),
        parser_registry=StubRegistry(),
        ollama_client=StubOllamaClient(),
        normalizer=TradeExtractionNormalizer(),
    )

    payload = service.review_pdf_bytes(filename="nota_xp.pdf", file_bytes=b"%PDF-1.4 fake", import_batch_id="pdf-batch-123")

    assert payload.review_required is False
    assert payload.filename == "nota_xp.pdf"
    assert payload.normalized_broker == "XP"
    assert payload.normalized_trade_date == date(2026, 3, 20)
    assert payload.llm.model == "stub-model"
    assert payload.llm.base_url == "http://localhost:11434"
    assert payload.llm.request_succeeded is True
    assert payload.llm.json_valid is True
    assert payload.llm.fallback_used is False
    assert payload.llm.raw_response == '{"ok": true}'
    assert len(payload.trades) == 1
    assert payload.trades[0].source_type == TradeSourceType.PDF_IMPORT
    assert payload.trades[0].imported_file_name == "nota_xp.pdf"
    assert payload.trades[0].import_batch_id == "pdf-batch-123"
    assert payload.trades[0].broker == "XP"
    assert payload.trades[0].net_result == Decimal("17.00")
    assert payload.trades[0].asset_ticker == "WIN"
    assert payload.trades[0].asset_classification == PDFAssetClassification.WIN
    assert payload.trades[0].trade_time == "09:15:00"
    assert payload.trades[0].ready_for_persistence is True


@pytest.fixture
def pdf_api_client(tmp_path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "pdf_import_api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "pdf-import-secret")

    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session: Session = TestingSessionLocal()
    try:
        AuthService(session).create_user(
            email="admin@smarttrade.local",
            password="super-secret",
            full_name="Smart Trade Admin",
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
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@smarttrade.local", "password": "super-secret"},
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_pdf_import_review_endpoint_returns_review_payload(
    pdf_api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_payload = PDFImportReviewPayload(
        filename="nota.pdf",
        broker_detection=BrokerDetectionResult(broker="XP", confidence=0.92, strategy="filename", evidence=["xp"]),
        normalized_broker="XP",
        normalized_trade_date=None,
        extraction=PDFExtractionMetadata(extractor_used="stub", page_count=1, extracted_characters=12, text_truncated=False),
        llm=OllamaInferenceMetadata(
            model="stub-model",
            base_url="http://localhost:11434",
            request_succeeded=True,
            json_valid=True,
            fallback_used=False,
            raw_response='{"trades":[]}',
        ),
        pages=[PDFPageText(page_number=1, text="nota fake", char_count=9)],
        extracted_text="nota fake",
        trades=[],
        warnings=[TradeReviewWarning(code="no_trades_extracted", message="No trades were extracted from the PDF.")],
        validation_errors=[],
        raw_json={"trades": []},
        review_required=True,
    )

    monkeypatch.setattr(
        PDFImportReviewService,
        "process_uploaded_stream",
        classmethod(lambda cls, filename, file_stream, import_batch_id=None: expected_payload),
    )

    response = pdf_api_client.post(
        "/imports/pdf/review",
        files={"file": ("nota.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["filename"] == "nota.pdf"
    assert payload["import_job"]["batch_id"].startswith("pdf-")
    assert payload["broker_detection"]["broker"] == "XP"
    assert payload["normalized_broker"] == "XP"
    assert payload["llm"]["json_valid"] is True
    assert payload["review_required"] is True


def test_pdf_import_review_endpoint_rejects_non_pdf_file(pdf_api_client: TestClient) -> None:
    response = pdf_api_client.post(
        "/imports/pdf/review",
        files={"file": ("nota.txt", b"nao pdf", "text/plain")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "document_import_error"


def test_pdf_import_review_endpoint_rejects_large_payload(
    pdf_api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_import_route_module, "MAX_PDF_UPLOAD_SIZE_BYTES", 8)

    response = pdf_api_client.post(
        "/imports/pdf/review",
        files={"file": ("nota.pdf", b"123456789", "application/pdf")},
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "upload_too_large"
