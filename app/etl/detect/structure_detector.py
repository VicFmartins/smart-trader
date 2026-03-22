from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from io import StringIO
import logging
from pathlib import Path

import pandas as pd

from app.core.exceptions import ETLInputError
from app.etl.detect.column_mapper import FuzzyColumnMapper
from app.etl.transform.parsers import is_blankish, normalize_text


logger = logging.getLogger(__name__)

CSV_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
CSV_SEPARATORS: tuple[str, ...] = (";", ",", "\t", "|")
MAX_HEADER_SCAN_ROWS = 8


@dataclass(frozen=True, slots=True)
class StructureDetection:
    file_type: str
    delimiter: str | None = None
    header_row: int = 0
    sheet_name: str | None = None
    encoding: str | None = None
    score: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StructureDetectionResult:
    dataframe: pd.DataFrame
    detection: StructureDetection


class StructureDetector:
    def __init__(self, *, mapper: FuzzyColumnMapper | None = None) -> None:
        self.mapper = mapper or FuzzyColumnMapper()

    def read(self, file_path: Path) -> StructureDetectionResult:
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            return self._read_csv(file_path)
        if suffix in {".xlsx", ".xls"}:
            return self._read_excel(file_path)
        raise ETLInputError(f"Unsupported file type for smart tabular detection: {suffix}")

    def _read_csv(self, file_path: Path) -> StructureDetectionResult:
        csv_text, encoding = self._decode_csv_text(file_path)
        best_candidate: tuple[float, str, int, pd.DataFrame] | None = None

        for separator in CSV_SEPARATORS:
            try:
                rows = list(csv.reader(StringIO(csv_text), delimiter=separator))
            except Exception:
                continue
            max_columns = max((len(row) for row in rows), default=0)
            if max_columns == 0:
                continue
            normalized_rows = [row + [""] * (max_columns - len(row)) for row in rows]
            raw_frame = pd.DataFrame(normalized_rows, dtype=str)

            candidate = self._score_frame_candidates(raw_frame, delimiter=separator)
            if candidate is None:
                continue
            score, header_row = candidate
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (score, separator, header_row, raw_frame)

        if best_candidate is None:
            raise ETLInputError(f"Unable to detect a usable CSV structure for {file_path}")

        score, separator, header_row, raw_frame = best_candidate
        dataframe = self._frame_from_header(raw_frame, header_row)
        return StructureDetectionResult(
            dataframe=dataframe,
            detection=StructureDetection(
                file_type="csv",
                delimiter=separator,
                header_row=header_row,
                encoding=encoding,
                score=round(score, 2),
            ),
        )

    def _read_excel(self, file_path: Path) -> StructureDetectionResult:
        excel_file = pd.ExcelFile(file_path)
        best_candidate: tuple[float, str, int, pd.DataFrame] | None = None
        for sheet_name in excel_file.sheet_names:
            raw_frame = excel_file.parse(sheet_name=sheet_name, header=None, dtype=str)
            candidate = self._score_frame_candidates(raw_frame, delimiter=None)
            if candidate is None:
                continue
            score, header_row = candidate
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (score, sheet_name, header_row, raw_frame)

        if best_candidate is None:
            raise ETLInputError(f"Unable to detect a usable worksheet structure for {file_path}")

        score, sheet_name, header_row, raw_frame = best_candidate
        dataframe = self._frame_from_header(raw_frame, header_row)
        return StructureDetectionResult(
            dataframe=dataframe,
            detection=StructureDetection(
                file_type="excel",
                header_row=header_row,
                sheet_name=sheet_name,
                score=round(score, 2),
            ),
        )

    def _score_frame_candidates(self, raw_frame: pd.DataFrame, *, delimiter: str | None) -> tuple[float, int] | None:
        cleaned = raw_frame.dropna(how="all").dropna(axis=1, how="all")
        if cleaned.empty:
            return None

        best_score = float("-inf")
        best_header_row = 0
        max_rows = min(MAX_HEADER_SCAN_ROWS, len(cleaned))
        for header_row in range(max_rows):
            row_values = [normalize_text(value, "") for value in cleaned.iloc[header_row].tolist()]
            non_blank = [value for value in row_values if not is_blankish(value)]
            if len(non_blank) < 2:
                continue

            mapping_results = self.mapper.map_columns(non_blank)
            mapped_scores = [result.score for result in mapping_results if result.accepted]
            mapped_count = len(mapped_scores)
            numeric_like = sum(1 for value in non_blank if _looks_numericish(value))
            uniqueness_ratio = len(set(non_blank)) / len(non_blank) if non_blank else 0.0
            score = (
                mapped_count * 18.0
                + sum(mapped_scores) * 0.12
                + len(non_blank) * 2.0
                + uniqueness_ratio * 10.0
                - numeric_like * 6.0
            )
            if delimiter == "," and len(cleaned.columns) == 1:
                score -= 15.0

            if score > best_score:
                best_score = score
                best_header_row = header_row

        if best_score == float("-inf"):
            return None
        return best_score, best_header_row

    def _frame_from_header(self, raw_frame: pd.DataFrame, header_row: int) -> pd.DataFrame:
        cleaned = raw_frame.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
        header_values = [normalize_text(value, f"column_{index}") for index, value in enumerate(cleaned.iloc[header_row].tolist())]
        unique_headers = _make_unique_headers(header_values)
        data = cleaned.iloc[header_row + 1 :].copy()
        data.columns = unique_headers
        return data.reset_index(drop=True)

    def _decode_csv_text(self, file_path: Path) -> tuple[str, str]:
        raw_bytes = file_path.read_bytes()
        last_error: UnicodeDecodeError | None = None
        for encoding in CSV_ENCODINGS:
            try:
                return raw_bytes.decode(encoding), encoding
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise ETLInputError(f"Unable to decode CSV file {file_path}: {last_error}") from last_error
        raise ETLInputError(f"Unable to decode CSV file {file_path}")


def _make_unique_headers(headers: list[str]) -> list[str]:
    unique_headers: list[str] = []
    seen_counts: dict[str, int] = {}
    for index, header in enumerate(headers):
        base = header or f"column_{index}"
        count = seen_counts.get(base, 0)
        seen_counts[base] = count + 1
        unique_headers.append(base if count == 0 else f"{base}_{count + 1}")
    return unique_headers


def _looks_numericish(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    allowed = set("0123456789.,-/%R$ ")
    return all(character in allowed for character in stripped)
