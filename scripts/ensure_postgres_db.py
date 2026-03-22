from __future__ import annotations

from pathlib import Path
import sys

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.is_postgresql:
        raise SystemExit("DATABASE_URL must point to PostgreSQL to use this helper.")

    url = make_url(settings.database_url)
    database_name = url.database
    if not database_name:
        raise SystemExit("DATABASE_URL must include a database name.")

    admin_connection = psycopg.connect(
        host=url.host or "localhost",
        port=url.port or 5432,
        user=url.username or "postgres",
        password=url.password or "",
        dbname="postgres",
        autocommit=True,
    )

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            exists = cursor.fetchone() is not None
            if exists:
                print(f"Database '{database_name}' already exists.")
            else:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
                print(f"Database '{database_name}' created successfully.")
    finally:
        admin_connection.close()


if __name__ == "__main__":
    main()
