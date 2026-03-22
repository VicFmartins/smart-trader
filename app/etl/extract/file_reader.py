from __future__ import annotations

from io import StringIO
import logging
from pathlib import Path

import pandas as pd
from pandas.errors import ParserError

from app.core.config import get_settings
from app.core.exceptions import ETLInputError
from app.etl.detect.column_mapper import FuzzyColumnMapper, build_layout_signature
from app.etl.detect.review_queue import evaluate_review_decision
from app.etl.detect.structure_detector import StructureDetector
from app.etl.extract.xp_common import detect_xp_file_kind
from app.etl.extract.xp_json_parser import XPJsonParser
from app.etl.extract.xp_movements_parser import XPMovementsParser
from app.etl.extract.xp_position_parser import XPPositionParser


logger = logging.getLogger(__name__)

CSV_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
CSV_SEPARATORS: tuple[str | None, ...] = (None, ";", ",", "\t", "|")


def discover_input_files(directory: Path) -> list[Path]:
    settings = get_settings()
    directory.mkdir(parents=True, exist_ok=True)
    files = [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in settings.supported_extensions]
    return sorted(files)


class FileReader:
    def __init__(self, *, mapping_resolver=None, mapper: FuzzyColumnMapper | None = None) -> None:
        self.position_parser = XPPositionParser()
        self.movements_parser = XPMovementsParser()
        self.json_parser = XPJsonParser()
        self.column_mapper = mapper or FuzzyColumnMapper()
        self.structure_detector = StructureDetector(mapper=self.column_mapper)
        self.mapping_resolver = mapping_resolver

    def read(self, file_path: Path) -> pd.DataFrame:
        if not file_path.exists() or not file_path.is_file():
            raise ETLInputError(f"Input file does not exist: {file_path}")

        parser_kind = detect_xp_file_kind(file_path)
        if parser_kind is not None:
            dataframe = self._read_xp_file(file_path, parser_kind)
        else:
            dataframe = self._read_generic_file(file_path)

        dataframe = dataframe.dropna(how="all").dropna(axis=1, how="all")
        if dataframe.empty:
            raise ETLInputError(f"Input file has no usable rows: {file_path}")
        dataframe.attrs.setdefault("source_filename", file_path.name)
        dataframe.attrs.setdefault("source_path", str(file_path))
        return dataframe

    def _read_generic_file(self, file_path: Path) -> pd.DataFrame:
        suffix = file_path.suffix.lower()
        try:
            detection_result = self.structure_detector.read(file_path)
            original_columns = list(detection_result.dataframe.columns)
            dataframe = detection_result.dataframe
            layout_signature = build_layout_signature(original_columns)
            preferred_mappings = self.mapping_resolver(layout_signature) if self.mapping_resolver is not None else {}
            mapping_results = self.column_mapper.map_columns(list(dataframe.columns), preferred_mappings=preferred_mappings)
            renamed_columns = self.column_mapper.apply_mapping(list(dataframe.columns), mapping_results)
            dataframe = dataframe.rename(columns=renamed_columns)
            review_decision = evaluate_review_decision(mapping_results)
            dataframe.attrs["parser_name"] = "smart_tabular_reader"
            dataframe.attrs["detected_columns"] = original_columns
            dataframe.attrs["layout_signature"] = layout_signature
            dataframe.attrs["structure_detection"] = detection_result.detection.as_dict()
            dataframe.attrs["column_mapping"] = [result.as_dict() for result in mapping_results]
            dataframe.attrs["review_decision"] = review_decision.as_dict()
            dataframe.attrs["review_required"] = review_decision.review_required
            dataframe.attrs["detection_confidence"] = review_decision.confidence_score
            logger.info(
                "Smart detection succeeded for %s with confidence %.2f and review_required=%s",
                file_path,
                review_decision.confidence_score,
                review_decision.review_required,
            )
            if review_decision.review_required:
                logger.warning("Smart detection flagged %s for review: %s", file_path, review_decision.reasons)
            return dataframe
        except ETLInputError:
            logger.warning("Smart tabular detection failed for %s. Falling back to legacy reader.", file_path)

        if suffix == ".csv":
            return self._read_csv(file_path)
        if suffix in {".xlsx", ".xls"}:
            dataframe = pd.read_excel(file_path, dtype=str)
            dataframe.attrs["parser_name"] = "generic_excel_reader"
            dataframe.attrs["detected_columns"] = list(dataframe.columns)
            dataframe.attrs["layout_signature"] = build_layout_signature(list(dataframe.columns))
            return dataframe
        raise ETLInputError(f"Unsupported input file type: {suffix}")

    def _read_xp_file(self, file_path: Path, parser_kind: str) -> pd.DataFrame:
        if parser_kind == "xp_position":
            dataframe = self.position_parser.parse(file_path)
            dataframe.attrs["parser_name"] = self.position_parser.name
            return dataframe
        if parser_kind == "xp_movements":
            dataframe = self.movements_parser.parse(file_path)
            dataframe.attrs["parser_name"] = self.movements_parser.name
            return dataframe
        if parser_kind == "xp_json":
            dataframe = self.json_parser.parse(file_path)
            dataframe.attrs["parser_name"] = self.json_parser.name
            return dataframe
        raise ETLInputError(f"Unsupported XP input file type for {file_path}")

    def _read_csv(self, file_path: Path) -> pd.DataFrame:
        csv_text, encoding = self._decode_csv_text(file_path)
        for separator in CSV_SEPARATORS:
            try:
                dataframe = pd.read_csv(
                    StringIO(csv_text),
                    sep=separator,
                    engine="python",
                    dtype=str,
                    skipinitialspace=True,
                )
                logger.info(
                    "Read CSV file %s using encoding=%s separator=%s",
                    file_path,
                    encoding,
                    "auto" if separator is None else separator,
                )
                dataframe.attrs["parser_name"] = "generic_csv_reader"
                dataframe.attrs["detected_columns"] = list(dataframe.columns)
                dataframe.attrs["layout_signature"] = build_layout_signature(list(dataframe.columns))
                return dataframe
            except ParserError:
                continue
        raise ETLInputError(f"Unable to decode CSV file with supported encodings: {file_path}")

    def _decode_csv_text(self, file_path: Path) -> tuple[str, str]:
        raw_bytes = file_path.read_bytes()
        last_error: UnicodeDecodeError | None = None

        for encoding in CSV_ENCODINGS:
            try:
                decoded_text = raw_bytes.decode(encoding)
                return decoded_text, encoding
            except UnicodeDecodeError as exc:
                last_error = exc
                continue

        message = f"Unable to decode CSV file with supported encodings: {file_path}"
        if last_error is not None:
            raise ETLInputError(f"{message}. Last decode error: {last_error}") from last_error
        raise ETLInputError(message)
