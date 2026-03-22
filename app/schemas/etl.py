from pydantic import BaseModel, Field, field_validator


class ETLRunRequest(BaseModel):
    source_path: str | None = Field(
        default=None,
        description="Optional file path. If omitted, the service processes local raw files or the bundled sample.",
    )

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ETLRunFromS3Request(BaseModel):
    s3_key: str | None = Field(
        default=None,
        description="Optional exact S3 object key. If omitted, the latest file under the prefix is used.",
    )
    s3_prefix: str | None = Field(
        default=None,
        description="Optional S3 prefix used to find the latest file.",
    )

    @field_validator("s3_key", "s3_prefix")
    @classmethod
    def validate_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ETLFileResult(BaseModel):
    ingestion_report_id: int | None = None
    source_file: str
    raw_file: str
    processed_file: str
    rows_processed: int = Field(ge=0)
    rows_skipped: int = Field(ge=0)
    clients_created: int = Field(ge=0)
    accounts_created: int = Field(ge=0)
    assets_created: int = Field(ge=0)
    positions_upserted: int = Field(ge=0)
    detection_confidence: float | None = None
    review_required: bool = False
    review_status: str | None = None
    review_reasons: list[str] = Field(default_factory=list)


class ETLRunResponse(BaseModel):
    status: str = "success"
    files_processed: int = Field(ge=0)
    total_rows_processed: int = Field(ge=0)
    total_rows_skipped: int = Field(ge=0)
    results: list[ETLFileResult]


class UploadResponse(BaseModel):
    ingestion_report_id: int | None = None
    filename: str
    detected_type: str
    rows_processed: int = Field(ge=0)
    rows_skipped: int = Field(ge=0)
    message: str
    processed_at: str
    raw_file: str
    processed_file: str
    detection_confidence: float | None = None
    review_required: bool = False
    review_status: str | None = None
    review_reasons: list[str] = Field(default_factory=list)
    reprocessed_at: str | None = None
    reprocess_count: int = Field(default=0, ge=0)
