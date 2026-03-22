from __future__ import annotations

from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import ENV_FILE, get_settings
from app.services.storage_service import S3StorageService


def main() -> None:
    settings = get_settings()
    print(f"Using env file: {ENV_FILE}")
    print(f"Using bucket: {settings.s3_bucket_name}")
    print(f"Using prefix: {settings.s3_bucket_prefix}")

    storage = S3StorageService()
    storage.verify_bucket_access()
    files = storage.list_files(prefix=settings.s3_bucket_prefix)
    print(f"S3 access verified. Found {len(files)} object(s) under prefix '{settings.s3_bucket_prefix}'.")
    if files:
        latest = files[0]
        print(f"Latest object: s3://{settings.s3_bucket_name}/{latest.key}")


if __name__ == "__main__":
    main()
