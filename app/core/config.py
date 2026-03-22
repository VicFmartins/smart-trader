from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
VALID_STORAGE_MODES = {"local", "s3"}
VALID_ALERT_PROVIDERS = {"noop", "log", "sns"}
VALID_LLM_PROVIDERS = {"ollama", "gemini"}


def _default_sqlite_database_url() -> str:
    database_path = (BASE_DIR / "data" / "smart_trade.db").resolve()
    return f"sqlite:///{database_path.as_posix()}"


def _get_env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    project_name: str
    app_env: str
    app_version: str
    log_level: str
    database_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_default_region: str
    s3_endpoint_url: str
    s3_use_path_style: bool
    s3_bucket_name: str
    s3_bucket_prefix: str
    default_risk_profile: str
    raw_storage_mode: str
    auto_create_tables: bool
    api_prefix: str
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    alerts_enabled: bool
    alert_provider: str
    alert_sns_topic_arn: str
    infer_missing_broker: bool
    default_broker_name: str
    etl_soft_validation_mode: bool
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    pdf_import_max_pages: int
    pdf_import_max_chars: int
    default_admin_email: str
    default_admin_password: str
    smart_trade_api_url: str
    llm_provider: str
    gemini_api_key: str
    gemini_model: str
    gemini_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        log_level = _get_env("LOG_LEVEL", "INFO").upper()
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid LOG_LEVEL '{log_level}'. Expected one of: {sorted(VALID_LOG_LEVELS)}")

        raw_storage_mode = _get_env("RAW_STORAGE_MODE", "local").lower()
        if raw_storage_mode not in VALID_STORAGE_MODES:
            raise ValueError(
                f"Invalid RAW_STORAGE_MODE '{raw_storage_mode}'. Expected one of: {sorted(VALID_STORAGE_MODES)}"
            )

        jwt_access_token_expire_minutes = _get_int_env("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60)
        if jwt_access_token_expire_minutes <= 0:
            raise ValueError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero.")

        ollama_timeout_seconds = _get_int_env("OLLAMA_TIMEOUT_SECONDS", 120)
        if ollama_timeout_seconds <= 0:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than zero.")

        llm_provider = _get_env("LLM_PROVIDER", "ollama").lower()
        if llm_provider not in VALID_LLM_PROVIDERS:
            raise ValueError(f"Invalid LLM_PROVIDER '{llm_provider}'. Expected one of: {sorted(VALID_LLM_PROVIDERS)}")

        gemini_timeout_seconds = _get_int_env("GEMINI_TIMEOUT_SECONDS", 60)
        if gemini_timeout_seconds <= 0:
            raise ValueError("GEMINI_TIMEOUT_SECONDS must be greater than zero.")

        pdf_import_max_pages = _get_int_env("PDF_IMPORT_MAX_PAGES", 50)
        if pdf_import_max_pages <= 0:
            raise ValueError("PDF_IMPORT_MAX_PAGES must be greater than zero.")

        pdf_import_max_chars = _get_int_env("PDF_IMPORT_MAX_CHARS", 50000)
        if pdf_import_max_chars <= 0:
            raise ValueError("PDF_IMPORT_MAX_CHARS must be greater than zero.")

        alert_provider = _get_env("ALERT_PROVIDER", "noop").lower()
        if alert_provider not in VALID_ALERT_PROVIDERS:
            raise ValueError(
                f"Invalid ALERT_PROVIDER '{alert_provider}'. Expected one of: {sorted(VALID_ALERT_PROVIDERS)}"
            )

        return cls(
            project_name=_get_env("PROJECT_NAME", "Smart Trade"),
            app_env=_get_env("APP_ENV", "development"),
            app_version=_get_env("APP_VERSION", "0.1.0"),
            log_level=log_level,
            database_url=_get_env(
                "DATABASE_URL",
                _default_sqlite_database_url(),
            ),
            aws_access_key_id=_get_env("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=_get_env("AWS_SECRET_ACCESS_KEY", ""),
            aws_default_region=_get_env("AWS_DEFAULT_REGION", _get_env("AWS_REGION", "us-east-1")),
            s3_endpoint_url=_get_env(
                "S3_ENDPOINT_URL",
                _get_env("AWS_ENDPOINT_URL", _get_env("AWS_S3_ENDPOINT_URL", "")),
            ),
            s3_use_path_style=_get_bool_env("S3_USE_PATH_STYLE", _get_bool_env("AWS_S3_FORCE_PATH_STYLE", False)),
            s3_bucket_name=_get_env("S3_BUCKET_NAME", _get_env("AWS_S3_BUCKET", "")),
            s3_bucket_prefix=_get_env("S3_BUCKET_PREFIX", "incoming/"),
            default_risk_profile=_get_env("DEFAULT_RISK_PROFILE", "moderado").lower(),
            raw_storage_mode=raw_storage_mode,
            auto_create_tables=_get_bool_env("AUTO_CREATE_TABLES", True),
            api_prefix=_get_env("API_PREFIX", ""),
            jwt_secret_key=_get_env("JWT_SECRET_KEY", "change-me-before-production"),
            jwt_algorithm=_get_env("JWT_ALGORITHM", "HS256"),
            jwt_access_token_expire_minutes=jwt_access_token_expire_minutes,
            alerts_enabled=_get_bool_env("ALERTS_ENABLED", False),
            alert_provider=alert_provider,
            alert_sns_topic_arn=_get_env("ALERT_SNS_TOPIC_ARN", ""),
            infer_missing_broker=_get_bool_env("INFER_MISSING_BROKER", True),
            default_broker_name=_get_env("DEFAULT_BROKER_NAME", "UNKNOWN"),
            etl_soft_validation_mode=_get_bool_env("ETL_SOFT_VALIDATION_MODE", True),
            ollama_base_url=_get_env("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=_get_env("OLLAMA_MODEL", "llama3.1:8b"),
            ollama_timeout_seconds=ollama_timeout_seconds,
            pdf_import_max_pages=pdf_import_max_pages,
            pdf_import_max_chars=pdf_import_max_chars,
            default_admin_email=_get_env("DEFAULT_ADMIN_EMAIL", "admin@smarttrade.local"),
            default_admin_password=_get_env("DEFAULT_ADMIN_PASSWORD", "smarttrade123"),
            smart_trade_api_url=_get_env("SMART_TRADE_API_URL", "http://127.0.0.1:8010"),
            llm_provider=llm_provider,
            gemini_api_key=_get_env("GEMINI_API_KEY", ""),
            gemini_model=_get_env("GEMINI_MODEL", "gemini-2.0-flash-lite"),
            gemini_timeout_seconds=gemini_timeout_seconds,
        )

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_data_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def samples_dir(self) -> Path:
        return self.data_dir / "samples"

    @property
    def real_inputs_dir(self) -> Path:
        return self.data_dir / "real_inputs"

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".csv", ".xlsx", ".xls", ".json")

    @property
    def is_postgresql(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def database_backend(self) -> str:
        if self.is_sqlite:
            return "sqlite"
        if self.is_postgresql:
            return "postgresql"
        return "unknown"

    def ensure_directories(self) -> None:
        for directory in (self.data_dir, self.raw_data_dir, self.processed_data_dir, self.samples_dir, self.real_inputs_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def missing_s3_settings(self) -> list[str]:
        missing: list[str] = []
        if not self.s3_bucket_name:
            missing.append("S3_BUCKET_NAME")
        return missing

    def validate_s3_settings(self) -> None:
        missing = self.missing_s3_settings()
        if missing:
            raise ValueError(
                "Missing required S3 configuration: "
                + ", ".join(missing)
                + f". Update {ENV_FILE} or your shell environment."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(ENV_FILE, override=False)
    return Settings.from_env()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
