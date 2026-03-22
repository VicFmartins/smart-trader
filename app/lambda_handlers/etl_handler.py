from __future__ import annotations

import json
import logging

from app.core.config import get_settings
from app.core.exceptions import ApplicationError
from app.db.session import init_db, session_scope
from app.lambda_handlers.event_parser import resolve_lambda_invocation
from app.services.import_pipeline import ImportPipelineService


ETLService = ImportPipelineService


logger = logging.getLogger(__name__)


def _lambda_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=str),
    }

def handler(event: dict | str | None, context: object | None) -> dict:
    del context

    try:
        settings = get_settings()
        invocation = resolve_lambda_invocation(event)

        settings.ensure_directories()
        init_db()

        with session_scope() as session:
            service = ETLService(session)
            result = service.run_from_lambda_invocation(invocation)

        logger.info(
            "Lambda ETL invocation completed successfully: type=%s files_processed=%s total_rows_processed=%s",
            invocation.invocation_type,
            result.files_processed,
            result.total_rows_processed,
        )
        payload = result.model_dump(mode="json")
        payload["invocation"] = {
            "type": invocation.invocation_type,
            "records_received": len(invocation.s3_objects) if invocation.s3_objects else 1,
            "s3_objects": [
                {
                    "bucket_name": item.bucket_name,
                    "object_key": item.object_key,
                    "delivery_source": item.delivery_source,
                }
                for item in invocation.s3_objects
            ],
        }
        return _lambda_response(200, payload)
    except ApplicationError as exc:
        logger.exception("Lambda ETL invocation failed with an application error.")
        return _lambda_response(
            400,
            {"status": "error", "error": {"code": exc.error_code, "message": exc.message}},
        )
    except json.JSONDecodeError as exc:
        logger.exception("Lambda ETL invocation received invalid JSON.")
        return _lambda_response(
            400,
            {
                "status": "error",
                "error": {
                    "code": "invalid_json",
                    "message": f"Unable to parse Lambda payload as JSON: {exc.msg}",
                },
            },
        )
    except Exception as exc:  # pragma: no cover - defensive runtime path
        logger.exception("Lambda ETL invocation failed unexpectedly.")
        return _lambda_response(
            500,
            {
                "status": "error",
                "error": {"code": "internal_server_error", "message": str(exc)},
            },
        )
