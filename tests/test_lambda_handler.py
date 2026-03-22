import json
from contextlib import contextmanager
from pathlib import Path

from app.lambda_handlers import etl_handler
from app.lambda_handlers.event_parser import extract_s3_objects, resolve_lambda_invocation
from app.schemas.etl import ETLFileResult, ETLRunResponse


class DummySettings:
    s3_bucket_name = "carteiraconsol-vi-001"

    def ensure_directories(self) -> None:
        return None


def build_result(source_file: str) -> ETLRunResponse:
    return ETLRunResponse(
        files_processed=1,
        total_rows_processed=6,
        total_rows_skipped=0,
        results=[
            ETLFileResult(
                source_file=source_file,
                raw_file="data/raw/sample_portfolio.csv",
                processed_file="data/processed/sample_portfolio.csv",
                rows_processed=6,
                rows_skipped=0,
                clients_created=1,
                accounts_created=1,
                assets_created=1,
                positions_upserted=6,
            )
        ],
    )


@contextmanager
def dummy_session_scope():
    yield object()


def test_lambda_handler_accepts_direct_s3_payload(monkeypatch) -> None:
    captured: dict = {}

    class FakeService:
        def __init__(self, session) -> None:
            captured["session"] = session

        def run_from_lambda_invocation(self, invocation):
            captured["invocation_type"] = invocation.invocation_type
            captured["s3_key"] = invocation.s3_key
            captured["s3_prefix"] = invocation.s3_prefix
            return build_result(f"s3://bucket/{invocation.s3_key}")

    monkeypatch.setattr(etl_handler, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(etl_handler, "init_db", lambda: None)
    monkeypatch.setattr(etl_handler, "session_scope", dummy_session_scope)
    monkeypatch.setattr(etl_handler, "ETLService", FakeService)

    response = etl_handler.handler({"s3_key": "incoming/sample_portfolio.csv"}, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "success"
    assert body["files_processed"] == 1
    assert body["invocation"]["type"] == "direct_s3"
    assert captured["invocation_type"] == "direct_s3"
    assert captured["s3_key"] == "incoming/sample_portfolio.csv"


def test_lambda_handler_accepts_s3_event_payload(monkeypatch) -> None:
    captured: dict = {}

    class FakeService:
        def __init__(self, session) -> None:
            captured["session"] = session

        def run_from_lambda_invocation(self, invocation):
            captured["invocation_type"] = invocation.invocation_type
            captured["s3_objects"] = list(invocation.s3_objects)
            return build_result(f"s3://{captured['s3_objects'][0].bucket_name}/{captured['s3_objects'][0].object_key}")

    monkeypatch.setattr(etl_handler, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(etl_handler, "init_db", lambda: None)
    monkeypatch.setattr(etl_handler, "session_scope", dummy_session_scope)
    monkeypatch.setattr(etl_handler, "ETLService", FakeService)

    response = etl_handler.handler(
        {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "carteiraconsol-vi-001"},
                        "object": {"key": "incoming%2Fsample_portfolio.csv"},
                    }
                }
            ]
        },
        None,
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "success"
    assert body["invocation"]["type"] == "s3_event"
    assert captured["invocation_type"] == "s3_event"
    assert captured["s3_objects"][0].bucket_name == "carteiraconsol-vi-001"
    assert captured["s3_objects"][0].object_key == "incoming/sample_portfolio.csv"


def test_lambda_event_parser_supports_sqs_wrapped_s3_event() -> None:
    fixture_path = Path("tests/fixtures/lambda_sqs_s3_event.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    invocation = resolve_lambda_invocation(payload)

    assert invocation.invocation_type == "s3_event"
    assert len(invocation.s3_objects) == 1
    assert invocation.s3_objects[0].bucket_name == "carteiraconsol-vi-001"
    assert invocation.s3_objects[0].object_key == "incoming/sample_portfolio.csv"
    assert invocation.s3_objects[0].delivery_source == "sqs"


def test_lambda_event_parser_loads_direct_s3_fixture() -> None:
    fixture_path = Path("tests/fixtures/lambda_s3_event.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    objects = extract_s3_objects(payload)

    assert len(objects) == 1
    assert objects[0].bucket_name == "carteiraconsol-vi-001"
    assert objects[0].object_key == "incoming/sample_portfolio.csv"
    assert objects[0].delivery_source == "s3"
