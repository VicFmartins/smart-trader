from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from app.core.exceptions import ETLInputError
from app.etl.transform.parsers import normalize_text, parse_reference_date, slugify_text


logger = logging.getLogger(__name__)

XP_POSITION_KEYWORDS = ("posicao inicial", "posição inicial", "posicao", "posição", "custodia", "custódia")
XP_MOVEMENTS_KEYWORDS = ("movimentacoes", "movimentações", "movimentacao", "movimentação", "extrato")
XP_JSON_KEYWORDS = ("posicao", "posição", "carteira", "portfolio", "custody", "holdings")
XP_BROKER_NAME = "XP"


def detect_xp_file_kind(file_path: Path) -> str | None:
    normalized_name = slugify_text(file_path.stem)
    suffix = file_path.suffix.lower()

    if suffix == ".json" and any(keyword in normalized_name for keyword in XP_JSON_KEYWORDS):
        return "xp_json"
    if suffix in {".xlsx", ".xls"}:
        if any(keyword in normalized_name for keyword in XP_MOVEMENTS_KEYWORDS):
            return "xp_movements"
        if any(keyword in normalized_name for keyword in XP_POSITION_KEYWORDS):
            return "xp_position"
    return None


def parse_date_from_filename(file_path: Path):
    for token in slugify_text(file_path.stem).split():
        parsed = parse_reference_date(token)
        if parsed is not None:
            return parsed
    return None


def select_excel_table(file_path: Path, column_aliases: dict[str, set[str]], *, min_matches: int = 2) -> pd.DataFrame:
    workbook = pd.ExcelFile(file_path)
    best_frame: pd.DataFrame | None = None
    best_score = -1

    for sheet_name in workbook.sheet_names:
        raw_sheet = workbook.parse(sheet_name=sheet_name, header=None, dtype=str)
        frame, score = _extract_table_from_sheet(raw_sheet, column_aliases, min_matches=min_matches)
        if frame is not None and score > best_score:
            best_frame = frame
            best_score = score

    if best_frame is None:
        raise ETLInputError(
            f"Unable to locate a usable XP table in workbook: {file_path}. "
            "Check whether the sheet contains recognizable portfolio columns."
        )

    logger.info("Selected XP workbook table from %s with match score=%s", file_path, best_score)
    return best_frame


def rename_columns_by_alias(frame: pd.DataFrame, column_aliases: dict[str, set[str]]) -> pd.DataFrame:
    renamed_columns: dict[str, str] = {}
    for column in frame.columns:
        normalized = slugify_text(str(column))
        for canonical_name, aliases in column_aliases.items():
            if normalized == canonical_name.replace("_", " ") or normalized in aliases:
                renamed_columns[column] = canonical_name
                break
        else:
            renamed_columns[column] = normalized.replace(" ", "_")
    renamed_frame = frame.rename(columns=renamed_columns)
    if not renamed_frame.columns.duplicated().any():
        return renamed_frame

    consolidated_columns: dict[str, pd.Series] = {}
    for column_name in dict.fromkeys(renamed_frame.columns):
        matching = renamed_frame.loc[:, renamed_frame.columns == column_name]
        if matching.shape[1] == 1:
            consolidated_columns[column_name] = matching.iloc[:, 0]
        else:
            consolidated_columns[column_name] = matching.bfill(axis=1).iloc[:, 0]
            logger.info("Consolidated %s duplicate XP columns into canonical column '%s'.", matching.shape[1], column_name)
    return pd.DataFrame(consolidated_columns)


def load_json_payload(file_path: Path):
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(file_path.read_text(encoding="cp1252"))
    except json.JSONDecodeError as exc:
        raise ETLInputError(f"Unable to parse JSON input file: {file_path}") from exc


def find_record_list(payload) -> list[dict]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload

    if isinstance(payload, dict):
        for value in payload.values():
            found = find_record_list(value)
            if found:
                return found

    if isinstance(payload, list):
        for item in payload:
            found = find_record_list(item)
            if found:
                return found

    return []


def sanitize_client_name(value: object, default: str = "XP Portfolio") -> str:
    return normalize_text(value, default)


def _extract_table_from_sheet(
    raw_sheet: pd.DataFrame,
    column_aliases: dict[str, set[str]],
    *,
    min_matches: int,
) -> tuple[pd.DataFrame | None, int]:
    expected_aliases = set()
    for aliases in column_aliases.values():
        expected_aliases.update(aliases)

    max_rows = min(len(raw_sheet), 20)
    best_frame: pd.DataFrame | None = None
    best_score = -1

    for row_index in range(max_rows):
        header_values = [slugify_text(str(value)) for value in raw_sheet.iloc[row_index].fillna("")]
        score = sum(1 for value in header_values if value in expected_aliases)
        if score < min_matches:
            continue

        header = [normalize_text(value, f"column_{index}") for index, value in enumerate(raw_sheet.iloc[row_index].tolist())]
        frame = raw_sheet.iloc[row_index + 1 :].copy()
        frame.columns = header
        frame = frame.dropna(how="all").dropna(axis=1, how="all")
        if frame.empty:
            continue

        if score > best_score:
            best_frame = frame
            best_score = score

    return best_frame, best_score
