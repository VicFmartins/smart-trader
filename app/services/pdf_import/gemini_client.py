from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.exceptions import InvalidLLMResponseError, ServiceUnavailableError
from app.services.pdf_import.ollama_client import OllamaChatResult


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"


class GeminiClient:
    """Google Gemini REST client with the same interface as OllamaClient.

    Uses the generateContent REST endpoint directly (no SDK dependency).
    chat_with_schema() sets responseMimeType=application/json so Gemini always
    returns syntactically valid JSON; the schema is also embedded in the prompt
    text so the model knows the expected structure.
    """

    def __init__(self, *, api_key: str, model: str, timeout_seconds: int) -> None:
        self.base_url = GEMINI_BASE_URL
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Public interface (mirrors OllamaClient)
    # ------------------------------------------------------------------

    def chat_with_schema(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> OllamaChatResult:
        """Send a prompt and request JSON output.

        The JSON schema is explicitly appended to the prompt so Gemini knows
        the exact field names required. responseMimeType=application/json
        enforces syntactically valid JSON output.
        """
        resolved_model = model or self.model
        schema_instruction = (
            "\n\nReturn JSON that exactly matches the following schema. "
            "Use ONLY the field names listed below — do not invent alternative names:\n"
            + json.dumps(schema, ensure_ascii=False, indent=2)
        )
        full_prompt = prompt + schema_instruction
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        return self._call(model=resolved_model, payload=payload)

    def chat(
        self,
        *,
        prompt: str,
        model: str | None = None,
    ) -> OllamaChatResult:
        """Plain text generation (used as fallback when schema mode fails)."""
        resolved_model = model or self.model
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0},
        }
        return self._call(model=resolved_model, payload=payload)

    def repair_json(
        self,
        *,
        invalid_response: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> OllamaChatResult:
        """Ask Gemini to fix a broken JSON response."""
        repair_prompt = (
            "You repair invalid JSON extracted from a brokerage note parser.\n"
            "Return only valid JSON matching this schema.\n"
            f"Schema:\n{json.dumps(schema, ensure_ascii=True)}\n\n"
            "Broken response:\n"
            f"{invalid_response}"
        )
        return self.chat_with_schema(prompt=repair_prompt, schema=schema, model=model)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call(self, *, model: str, payload: dict[str, Any]) -> OllamaChatResult:
        url = f"{self.base_url}/v1beta/models/{model}:generateContent"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload, params={"key": self._api_key})
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ServiceUnavailableError(
                f"Gemini returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("Unable to reach the Gemini API.") from exc

        body = response.json()
        try:
            content: str = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise InvalidLLMResponseError(
                "Gemini returned an unexpected response structure."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise InvalidLLMResponseError("Gemini returned an empty response.")

        return OllamaChatResult(model=model, content=content, response_json=body)
