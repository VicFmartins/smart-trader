from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import ENV_FILE, get_settings
from app.services.storage_service import S3StorageService


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a local portfolio file to the configured S3 bucket.")
    parser.add_argument("--file", required=True, dest="file_path", help="Local file path to upload.")
    parser.add_argument("--key", dest="key", help="Optional S3 object key.")
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_directories()
    print(f"Using env file: {ENV_FILE}")

    file_path = Path(args.file_path).expanduser().resolve()
    uploaded_key = S3StorageService().upload_file(file_path, key=args.key)
    print(f"Uploaded to s3://{settings.s3_bucket_name}/{uploaded_key}")


if __name__ == "__main__":
    main()
