from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from rapidfuzz import fuzz, process

from app.etl.detect.schema_registry import SchemaRegistry
from app.etl.transform.parsers import normalize_text, slugify_text


@dataclass(frozen=True, slots=True)
class ColumnMappingResult:
    original_name: str
    normalized_name: str
    canonical_name: str | None
    matched_alias: str | None
    score: float
    accepted: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class FuzzyColumnMapper:
    def __init__(self, *, registry: SchemaRegistry | None = None, threshold: float = 78.0) -> None:
        self.registry = registry or SchemaRegistry()
        self.threshold = threshold
        self._candidate_aliases: dict[str, tuple[str, str]] = {}
        for canonical_name, aliases in self.registry.alias_lookup().items():
            for alias in aliases:
                self._candidate_aliases[alias] = (canonical_name, alias)

    def map_columns(
        self,
        columns: Sequence[object],
        *,
        preferred_mappings: dict[str, str] | None = None,
    ) -> list[ColumnMappingResult]:
        raw_results = [self._map_single_column(column, preferred_mappings=preferred_mappings or {}) for column in columns]
        best_by_canonical: dict[str, ColumnMappingResult] = {}
        for result in raw_results:
            if result.canonical_name is None or not result.accepted:
                continue
            current = best_by_canonical.get(result.canonical_name)
            if current is None or result.score > current.score:
                best_by_canonical[result.canonical_name] = result

        final_results: list[ColumnMappingResult] = []
        for result in raw_results:
            if result.canonical_name is None or not result.accepted:
                final_results.append(result)
                continue
            if best_by_canonical.get(result.canonical_name) == result:
                final_results.append(result)
                continue
            final_results.append(
                ColumnMappingResult(
                    original_name=result.original_name,
                    normalized_name=result.normalized_name,
                    canonical_name=None,
                    matched_alias=result.matched_alias,
                    score=result.score,
                    accepted=False,
                )
            )
        return final_results

    def apply_mapping(self, columns: Sequence[object], mapping_results: Sequence[ColumnMappingResult]) -> dict[object, object]:
        renamed_columns: dict[object, object] = {}
        for original_column, result in zip(columns, mapping_results, strict=False):
            if result.accepted and result.canonical_name is not None:
                renamed_columns[original_column] = result.canonical_name
        return renamed_columns

    def _map_single_column(self, column: object, *, preferred_mappings: dict[str, str]) -> ColumnMappingResult:
        original_name = normalize_text(column, "")
        normalized_name = slugify_text(original_name)
        if not normalized_name:
            return ColumnMappingResult(original_name, normalized_name, None, None, 0.0, False)

        preferred_canonical = preferred_mappings.get(normalized_name)
        if preferred_canonical:
            return ColumnMappingResult(
                original_name=original_name,
                normalized_name=normalized_name,
                canonical_name=preferred_canonical,
                matched_alias="accepted_mapping",
                score=100.0,
                accepted=True,
            )

        if normalized_name in self._candidate_aliases:
            canonical_name, matched_alias = self._candidate_aliases[normalized_name]
            return ColumnMappingResult(original_name, normalized_name, canonical_name, matched_alias, 100.0, True)

        best_match = process.extractOne(
            normalized_name,
            list(self._candidate_aliases.keys()),
            scorer=fuzz.WRatio,
        )
        if best_match is None:
            return ColumnMappingResult(original_name, normalized_name, None, None, 0.0, False)

        matched_alias, score, _ = best_match
        canonical_name, _ = self._candidate_aliases[matched_alias]
        accepted = float(score) >= self.threshold
        return ColumnMappingResult(
            original_name=original_name,
            normalized_name=normalized_name,
            canonical_name=canonical_name if accepted else None,
            matched_alias=matched_alias,
            score=float(score),
            accepted=accepted,
        )


def build_layout_signature(columns: Sequence[object]) -> str:
    normalized_columns = [slugify_text(normalize_text(column, "")) for column in columns]
    filtered_columns = [column for column in normalized_columns if column]
    return "|".join(filtered_columns)
