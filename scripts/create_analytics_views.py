from __future__ import annotations

from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.db.session import get_engine, verify_db_connection


def _split_sql_statements(sql_script: str) -> list[str]:
    return [statement.strip() for statement in sql_script.split(";") if statement.strip()]


def main() -> None:
    settings = get_settings()
    sql_file = settings.base_dir / "sql" / "analytics_views.sql"

    if not sql_file.exists():
        raise FileNotFoundError(f"Analytics SQL file not found: {sql_file}")

    verify_db_connection()
    sql_script = sql_file.read_text(encoding="utf-8")
    statements = _split_sql_statements(sql_script)

    with get_engine().begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)

    print(f"Applied {len(statements)} analytics statements from: {sql_file}")


if __name__ == "__main__":
    main()
