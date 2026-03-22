from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote_plus

from app.core.exceptions import ETLInputError


@dataclass(frozen=True, slots=True)
class S3EventObject:
    bucket_name: str
    object_key: str
    delivery_source: str


@dataclass(frozen=True, slots=True)
class LambdaInvocation:
    invocation_type: str
    s3_objects: tuple[S3EventObject, ...] = ()
    s3_key: str | None = None
    s3_prefix: str | None = None
    source_path: str | None = None


def load_event_payload(event: dict[str, Any] | str | None) -> dict[str, Any]:
    if event is None:
        return {}
    if isinstance(event, str):
        loaded = json.loads(event)
        if not isinstance(loaded, dict):
            raise ETLInputError("Lambda payload must be a JSON object.")
        return loaded
    if not isinstance(event, dict):
        raise ETLInputError("Unsupported Lambda payload type. Expected a JSON object.")

    body = event.get("body")
    if isinstance(body, str) and body.strip():
        loaded = json.loads(body)
        if not isinstance(loaded, dict):
            raise ETLInputError("Lambda body must be a JSON object.")
        merged = dict(event)
        merged.pop("body", None)
        merged.update(loaded)
        return merged
    return event


def extract_s3_objects(payload: dict[str, Any]) -> list[S3EventObject]:
    records = payload.get("Records")
    if not isinstance(records, list):
        return []

    objects: list[S3EventObject] = []
    for record in records:
        objects.extend(_extract_s3_objects_from_record(record))
    return objects


def resolve_lambda_invocation(event: dict[str, Any] | str | None) -> LambdaInvocation:
    payload = load_event_payload(event)

    s3_objects = extract_s3_objects(payload)
    if s3_objects:
        return LambdaInvocation(invocation_type="s3_event", s3_objects=tuple(s3_objects))

    if payload.get("s3_key"):
        return LambdaInvocation(
            invocation_type="direct_s3",
            s3_key=str(payload["s3_key"]).strip(),
            s3_prefix=str(payload["s3_prefix"]).strip() if payload.get("s3_prefix") else None,
        )

    if payload.get("s3_prefix"):
        return LambdaInvocation(
            invocation_type="direct_s3",
            s3_prefix=str(payload["s3_prefix"]).strip(),
        )

    if payload.get("source_path"):
        return LambdaInvocation(
            invocation_type="direct_local",
            source_path=str(payload["source_path"]).strip(),
        )

    raise ETLInputError(
        "Unsupported Lambda payload. Provide 's3_key', 's3_prefix', 'source_path', or an S3/SQS event with Records[]."
    )


def _extract_s3_objects_from_record(record: Any) -> list[S3EventObject]:
    if not isinstance(record, dict):
        return []

    event_source = str(record.get("eventSource") or "").lower()
    if event_source == "aws:sqs":
        return _extract_s3_objects_from_sqs_record(record)

    return _extract_s3_objects_from_s3_record(record)


def _extract_s3_objects_from_sqs_record(record: dict[str, Any]) -> list[S3EventObject]:
    body = record.get("body")
    if not isinstance(body, str) or not body.strip():
        return []

    try:
        nested_payload = load_event_payload(body)
    except json.JSONDecodeError as exc:
        raise ETLInputError("Unable to parse nested SQS body as a JSON object.") from exc

    nested_objects = extract_s3_objects(nested_payload)
    if not nested_objects:
        return []

    return [
        S3EventObject(
            bucket_name=item.bucket_name,
            object_key=item.object_key,
            delivery_source="sqs",
        )
        for item in nested_objects
    ]


def _extract_s3_objects_from_s3_record(record: dict[str, Any]) -> list[S3EventObject]:
    s3_data = record.get("s3")
    if not isinstance(s3_data, dict):
        return []

    bucket_data = s3_data.get("bucket") or {}
    object_data = s3_data.get("object") or {}
    bucket_name = bucket_data.get("name")
    object_key = object_data.get("key")
    if not bucket_name or not object_key:
        return []

    return [
        S3EventObject(
            bucket_name=str(bucket_name),
            object_key=unquote_plus(str(object_key)),
            delivery_source="s3",
        )
    ]
