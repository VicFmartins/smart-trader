from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.db.session import init_db, verify_db_connection


if __name__ == "__main__":
    settings = get_settings()
    settings.ensure_directories()
    print(f"Initializing database schema using DATABASE_URL={settings.database_url}")
    if settings.is_postgresql:
        print("Detected PostgreSQL development flow.")
    elif settings.is_sqlite:
        print("Detected SQLite fallback flow.")

    verify_db_connection()
    init_db()
    print("Database schema ensured.")
