from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil

import pandas as pd

from app.core.config import get_settings


settings = get_settings()


def copy_file_with_timestamp(source_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    if source_path.parent.resolve() == target_dir.resolve():
        return source_path

    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    destination = target_dir / f"{timestamp}_{source_path.name}"

    shutil.copy2(source_path, destination)
    return destination


def write_dataframe_to_csv(dataframe: pd.DataFrame) -> Path:
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    destination = settings.processed_data_dir / f"normalized_positions_{timestamp}.csv"
    dataframe.to_csv(destination, index=False)
    return destination


def write_dataframe_snapshot(dataframe: pd.DataFrame, target_dir: Path, prefix: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    destination = target_dir / f"{prefix}_{timestamp}.csv"
    dataframe.to_csv(destination, index=False)
    return destination
