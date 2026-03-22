from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import text


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.db.session import get_engine, verify_db_connection


TABLES = ("clients", "accounts", "assets_master", "positions_history")


def main() -> None:
    settings = get_settings()
    print(f"Checking database using DATABASE_URL={settings.database_url}")
    verify_db_connection()

    engine = get_engine()
    with engine.connect() as connection:
        for table in TABLES:
            count = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            print(f"{table}: {count}")


if __name__ == "__main__":
    main()
