from __future__ import annotations

from app.main import app

try:
    from mangum import Mangum

    handler = Mangum(app)
except ImportError as import_error:  # pragma: no cover - optional runtime path
    _mangum_import_error = import_error

    def handler(event: dict | None, context: object | None) -> dict:
        raise RuntimeError(
            "Mangum is required to expose the FastAPI app through AWS Lambda/API Gateway."
        ) from _mangum_import_error
