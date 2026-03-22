from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True, slots=True)
class ParsedStructuredOutput(Generic[T]):
    payload: T | None
    raw_json: dict[str, Any] | list[Any] | None
    warnings: list[str]
    errors: list[str]
    cleaned_json_text: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.payload is not None


class StructuredOutputParser:
    def parse(self, raw_response: str, schema: type[T]) -> ParsedStructuredOutput[T]:
        warnings: list[str] = []
        errors: list[str] = []
        candidates = self._build_candidates(raw_response)

        for index, candidate in enumerate(candidates):
            try:
                raw_json = json.loads(candidate)
            except json.JSONDecodeError as exc:
                errors.append(f"Candidate {index + 1}: invalid JSON ({exc.msg}).")
                continue

            try:
                payload = schema.model_validate(raw_json)
                if index > 0:
                    warnings.append("Structured output required fallback JSON recovery.")
                return ParsedStructuredOutput(
                    payload=payload,
                    raw_json=raw_json,
                    warnings=warnings,
                    errors=errors,
                    cleaned_json_text=candidate,
                )
            except ValidationError as exc:
                errors.append(f"Candidate {index + 1}: schema validation failed ({exc.error_count()} errors).")

        return ParsedStructuredOutput(
            payload=None,
            raw_json=None,
            warnings=warnings,
            errors=errors or ["Model response did not contain valid JSON."],
            cleaned_json_text=candidates[0] if candidates else None,
        )

    def _build_candidates(self, raw_response: str) -> list[str]:
        candidates: list[str] = []
        cleaned = raw_response.strip()
        if cleaned:
            candidates.append(cleaned)

        fenced = CODE_FENCE_PATTERN.findall(raw_response)
        for match in fenced:
            stripped = match.strip()
            if stripped and stripped not in candidates:
                candidates.append(stripped)

        json_slice = self._extract_json_slice(raw_response)
        if json_slice and json_slice not in candidates:
            candidates.append(json_slice)

        normalized_candidates: list[str] = []
        for candidate in candidates:
            normalized = self._normalize_json(candidate)
            if normalized not in normalized_candidates:
                normalized_candidates.append(normalized)
        return normalized_candidates

    def _extract_json_slice(self, raw_response: str) -> str | None:
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return raw_response[start : end + 1].strip()

    def _normalize_json(self, candidate: str) -> str:
        normalized = candidate.replace("\u201c", '"').replace("\u201d", '"')
        normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
        normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)
        return normalized.strip()
