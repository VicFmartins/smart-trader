from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import ApplicationError, ETLInputError
from app.etl.extract.xp_common import detect_xp_file_kind
from app.etl.extract.xp_json_parser import XPJsonParser
from app.etl.extract.xp_movements_parser import XPMovementsParser
from app.etl.extract.xp_position_parser import XPPositionParser


logger = logging.getLogger(__name__)


class XPBundleParser:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.position_parser = XPPositionParser()
        self.movements_parser = XPMovementsParser()
        self.json_parser = XPJsonParser()

    def parse_directory(self, directory: Path) -> pd.DataFrame:
        files = self._discover_files(directory)
        if not files:
            raise ETLInputError(f"No supported XP input files were found in {directory}")
        classified_files = [(file_path, detect_xp_file_kind(file_path)) for file_path in files]
        has_snapshot_inputs = any(file_kind in {"xp_position", "xp_json"} for _, file_kind in classified_files)

        position_frames: list[pd.DataFrame] = []
        movements_frames: list[pd.DataFrame] = []
        json_frames: list[pd.DataFrame] = []
        parser_usage: dict[str, list[str]] = {"xp_position": [], "xp_movements": [], "xp_json": [], "skipped": []}
        parser_failures: list[str] = []

        for file_path, file_kind in classified_files:
            if has_snapshot_inputs and file_kind == "xp_movements":
                parser_usage["skipped"].append(file_path.name)
                logger.info("Skipping XP movement file %s because snapshot inputs are available in the same bundle.", file_path)
                continue
            try:
                if file_kind == "xp_position":
                    position_frames.append(self.position_parser.parse(file_path))
                    parser_usage["xp_position"].append(file_path.name)
                elif file_kind == "xp_movements":
                    movements_frames.append(self.movements_parser.parse(file_path))
                    parser_usage["xp_movements"].append(file_path.name)
                elif file_kind == "xp_json":
                    json_frames.append(self.json_parser.parse(file_path))
                    parser_usage["xp_json"].append(file_path.name)
                else:
                    parser_usage["skipped"].append(file_path.name)
                    logger.warning("Skipping unsupported real input file %s because no XP parser matched it.", file_path)
            except ApplicationError as exc:
                parser_failures.append(f"{file_path.name}: {exc.message}")
                logger.warning("XP parser failed for %s: %s", file_path, exc.message)

        selected_frames: list[pd.DataFrame] = []
        if json_frames:
            selected_frames.extend(json_frames)
            if position_frames:
                logger.info("XP real input bundle contains JSON and spreadsheet snapshots. JSON snapshot data will be preferred.")
        elif position_frames:
            selected_frames.extend(position_frames)
            if movements_frames:
                logger.info(
                    "XP real input bundle contains snapshot files and movement files. "
                    "Snapshot-derived positions will be loaded, and movement files are ignored for now."
                )
        else:
            selected_frames.extend(movements_frames)
            if movements_frames:
                logger.warning(
                    "XP real input bundle is using movement-derived positions without a snapshot file. "
                    "Quantities should be usable, but average prices are approximate."
                )

        if not selected_frames:
            raise ETLInputError(
                f"No XP files in {directory} could be converted into portfolio positions. "
                "Add files with names containing 'posicao', 'movimentacoes', or a position-oriented JSON payload."
            )

        combined = pd.concat(selected_frames, ignore_index=True)
        combined.attrs["parser_name"] = "xp_bundle_parser"
        combined.attrs["parser_usage"] = parser_usage
        combined.attrs["parser_failures"] = parser_failures
        return combined

    def _discover_files(self, directory: Path) -> list[Path]:
        return sorted(
            [
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.lower() in self.settings.supported_extensions
            ]
        )
