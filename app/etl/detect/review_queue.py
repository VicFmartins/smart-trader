from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean

from app.etl.detect.column_mapper import ColumnMappingResult
from app.etl.detect.schema_registry import SchemaRegistry


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    confidence_score: float
    review_required: bool
    mapped_columns: int
    total_columns: int
    missing_required_fields: tuple[str, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_review_decision(
    mapping_results: list[ColumnMappingResult],
    *,
    registry: SchemaRegistry | None = None,
) -> ReviewDecision:
    schema_registry = registry or SchemaRegistry()
    required_fields = set(schema_registry.required_confidence_fields())

    accepted_results = [result for result in mapping_results if result.accepted and result.canonical_name is not None]
    mapped_fields = {result.canonical_name for result in accepted_results if result.canonical_name is not None}
    total_columns = len(mapping_results)
    mapped_columns = len(accepted_results)
    missing_required_fields = tuple(sorted(required_fields - mapped_fields))

    reasons: list[str] = []
    if missing_required_fields:
        reasons.append(f"missing_required_fields:{', '.join(missing_required_fields)}")
    if mapped_columns < min(3, total_columns):
        reasons.append("too_few_columns_mapped")

    scores = [result.score for result in accepted_results]
    average_score = mean(scores) if scores else 0.0
    mapping_ratio = (mapped_columns / total_columns) if total_columns else 0.0
    required_penalty = 30.0 if missing_required_fields else 0.0
    confidence_score = max(0.0, min(100.0, average_score * 0.6 + mapping_ratio * 40.0 - required_penalty))
    review_required = bool(missing_required_fields) or mapped_columns < 3 or confidence_score < 65.0

    return ReviewDecision(
        confidence_score=round(confidence_score, 2),
        review_required=review_required,
        mapped_columns=mapped_columns,
        total_columns=total_columns,
        missing_required_fields=missing_required_fields,
        reasons=tuple(reasons),
    )
