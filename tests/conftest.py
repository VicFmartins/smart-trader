from pathlib import Path
import sys

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import clear_settings_cache
from app.db.session import clear_db_caches


@pytest.fixture(autouse=True)
def clear_runtime_caches() -> None:
    clear_db_caches()
    clear_settings_cache()
    yield
    clear_db_caches()
    clear_settings_cache()
