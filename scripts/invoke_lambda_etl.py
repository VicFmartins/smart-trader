import argparse
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import ENV_FILE, get_settings
from app.lambda_handlers.etl_handler import handler


def _load_payload_from_file(payload_file: str) -> dict:
    path = Path(payload_file).expanduser().resolve()
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _build_payload(args: argparse.Namespace) -> dict:
    if args.payload_file:
        return _load_payload_from_file(args.payload_file)

    if args.s3_event_key:
        settings = get_settings()
        return {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {"name": settings.s3_bucket_name},
                        "object": {"key": args.s3_event_key},
                    },
                }
            ]
        }

    if args.sqs_event_key:
        settings = get_settings()
        nested_event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {"name": settings.s3_bucket_name},
                        "object": {"key": args.sqs_event_key},
                    },
                }
            ]
        }
        return {
            "Records": [
                {
                    "messageId": "local-sqs-message",
                    "eventSource": "aws:sqs",
                    "body": json.dumps(nested_event),
                }
            ]
        }

    if args.s3_key:
        return {"s3_key": args.s3_key}

    if args.s3_prefix:
        return {"s3_prefix": args.s3_prefix}

    if args.source_path:
        return {"source_path": args.source_path}

    raise ValueError("Provide --payload-file, --s3-key, --s3-prefix, --s3-event-key, --sqs-event-key, or --source-path.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke the Lambda-compatible ETL handler locally.")
    parser.add_argument("--payload-file", dest="payload_file", help="Path to a JSON event payload file.")
    parser.add_argument("--s3-key", dest="s3_key", help="Invoke the Lambda handler with a direct S3 key payload.")
    parser.add_argument("--s3-prefix", dest="s3_prefix", help="Invoke the Lambda handler with a direct S3 prefix payload.")
    parser.add_argument(
        "--s3-event-key",
        dest="s3_event_key",
        help="Invoke the Lambda handler with a simulated S3 event using the configured bucket and this object key.",
    )
    parser.add_argument(
        "--sqs-event-key",
        dest="sqs_event_key",
        help="Invoke the Lambda handler with a simulated SQS message wrapping an S3 event for this object key.",
    )
    parser.add_argument("--source-path", dest="source_path", help="Invoke the Lambda handler with a local source_path payload.")
    args = parser.parse_args()

    payload = _build_payload(args)
    print(f"Using env file: {ENV_FILE}")
    print(json.dumps(payload, indent=2))
    response = handler(payload, None)

    body = response.get("body")
    if isinstance(body, str):
        try:
            response["body"] = json.loads(body)
        except json.JSONDecodeError:
            pass

    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
