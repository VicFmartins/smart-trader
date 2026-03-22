from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.services.storage_service import RawFileStorageService, S3ObjectInfo


class FakePaginator:
    def __init__(self, contents):
        self.contents = contents

    def paginate(self, Bucket, Prefix):
        return [{"Contents": self.contents}]


class FakeS3Client:
    def __init__(self):
        self.uploads = []
        self.downloads = []
        now = datetime.now(UTC)
        self.contents = [
            {"Key": "incoming/older.csv", "LastModified": now - timedelta(hours=1), "Size": 10},
            {"Key": "incoming/latest.csv", "LastModified": now, "Size": 11},
        ]

    def upload_file(self, source_path, bucket_name, object_key):
        self.uploads.append((source_path, bucket_name, object_key))

    def download_file(self, bucket_name, key, destination):
        self.downloads.append((bucket_name, key, destination))
        with open(destination, "w", encoding="utf-8") as file:
            file.write("Cliente;Corretora;Ativo;Qtd\nAna;XP;PETR4;1\n")

    def get_paginator(self, _operation_name):
        return FakePaginator(self.contents)


def test_s3_storage_fetches_latest_file_to_raw(monkeypatch, tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    sample_dir = tmp_path / "samples"
    processed_dir = tmp_path / "processed"
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("S3_BUCKET_PREFIX", "incoming/")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    fake_client = FakeS3Client()
    monkeypatch.setattr("app.services.storage_service.boto3.client", lambda *args, **kwargs: fake_client)
    monkeypatch.setattr("app.services.storage_service.get_settings", lambda: type(
        "Settings",
        (),
        {
            "raw_data_dir": raw_dir,
            "samples_dir": sample_dir,
            "processed_data_dir": processed_dir,
            "data_dir": tmp_path,
            "s3_bucket_name": "test-bucket",
            "s3_bucket_prefix": "incoming/",
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
            "aws_default_region": "us-east-1",
            "raw_storage_mode": "local",
            "validate_s3_settings": lambda self: None,
        },
    )())

    storage = RawFileStorageService()
    source_uri, local_path = storage.fetch_s3_file_to_raw()

    assert source_uri == "s3://test-bucket/incoming/latest.csv"
    assert local_path.exists()
    assert fake_client.downloads[0][1] == "incoming/latest.csv"


def test_s3_list_files_returns_latest_first(monkeypatch) -> None:
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    fake_client = FakeS3Client()
    monkeypatch.setattr("app.services.storage_service.boto3.client", lambda *args, **kwargs: fake_client)
    monkeypatch.setattr("app.services.storage_service.get_settings", lambda: type(
        "Settings",
        (),
        {
            "s3_bucket_name": "test-bucket",
            "s3_bucket_prefix": "incoming/",
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
            "aws_default_region": "us-east-1",
            "validate_s3_settings": lambda self: None,
        },
    )())

    from app.services.storage_service import S3StorageService

    files = S3StorageService().list_files()

    assert [item.key for item in files] == ["incoming/latest.csv", "incoming/older.csv"]


def test_raw_storage_in_s3_mode_returns_s3_uri_and_local_processing_path(monkeypatch, tmp_path) -> None:
    source_file = tmp_path / "portfolio.csv"
    source_file.write_text("cliente,ativo\nAna,PETR4\n", encoding="utf-8")

    uploaded: list[tuple[Path, str | None]] = []

    class FakeS3Storage:
        bucket_name = "test-bucket"

        def upload_file(self, source_path: Path, key: str | None = None) -> str:
            uploaded.append((source_path, key))
            return key or source_path.name

    monkeypatch.setattr("app.services.storage_service.get_settings", lambda: type(
        "Settings",
        (),
        {
            "raw_storage_mode": "s3",
            "raw_data_dir": tmp_path / "raw",
        },
    )())

    storage = RawFileStorageService()
    storage._s3_storage = FakeS3Storage()

    raw_reference, processing_path = storage.store_raw_file(source_file)

    assert raw_reference.startswith("s3://test-bucket/raw/")
    assert processing_path == source_file
    assert uploaded and uploaded[0][0] == source_file
