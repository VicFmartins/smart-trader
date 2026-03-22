from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base


logger = logging.getLogger(__name__)


def _build_engine() -> Engine:
    settings = get_settings()
    engine_kwargs = {"pool_pre_ping": True}
    if settings.is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    elif settings.is_postgresql:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
        engine_kwargs["pool_recycle"] = 1800
    return create_engine(settings.database_url, **engine_kwargs)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return _build_engine()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, expire_on_commit=False)


def _apply_sqlite_column_migrations(engine: Engine) -> None:
    """Add columns that were introduced after initial table creation.

    SQLite does not support DROP or complex ALTER TABLE, but supports ADD COLUMN.
    This function is idempotent — safe to run on every startup.
    """
    from sqlalchemy import inspect, text as sql_text

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    migrations: list[tuple[str, str, str]] = [
        # (table, column, DDL fragment)
        ("trades", "trade_time", "ALTER TABLE trades ADD COLUMN trade_time TIME"),
        ("trades", "contract_code", "ALTER TABLE trades ADD COLUMN contract_code VARCHAR(20)"),
    ]

    with engine.connect() as conn:
        for table, column, ddl in migrations:
            if table not in tables:
                continue
            existing_cols = {col["name"] for col in inspector.get_columns(table)}
            if column not in existing_cols:
                conn.execute(sql_text(ddl))
                conn.commit()
                logger.info("Applied column migration: %s.%s", table, column)


def init_db() -> None:
    import app.models  # noqa: F401

    # Development convenience only. Production environments should rely on
    # explicit, reviewed schema migrations instead of create_all().
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_column_migrations(engine)
    logger.info("Database schema ensured successfully.")


def verify_db_connection() -> None:
    settings = get_settings()
    engine = get_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Unable to connect to the configured database. "
            "Check DATABASE_URL and ensure the PostgreSQL database exists and is reachable."
        ) from exc
    logger.info("Database connection verified for %s.", "PostgreSQL" if settings.is_postgresql else "SQLite")


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def clear_db_caches() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
