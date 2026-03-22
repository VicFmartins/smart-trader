from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx

from app.core.exceptions import InvalidLLMResponseError, ServiceUnavailableError


@dataclass(frozen=True, slots=True)
class OllamaChatResult:
    model: str
    content: str
    response_json: dict[str, Any]


@runtime_checkable
class LLMChatClient(Protocol):
    """Structural protocol shared by OllamaClient and GeminiClient.

    Any object that exposes these attributes and methods can be used
    as the LLM backend in the PDF import pipeline.
    """

    model: str
    base_url: str

    def chat_with_schema(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> OllamaChatResult: ...

    def chat(
        self,
        *,
        prompt: str,
        model: str | None = None,
    ) -> OllamaChatResult: ...

    def repair_json(
        self,
        *,
        invalid_response: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> OllamaChatResult: ...


class OllamaClient:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def chat_with_schema(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> OllamaChatResult:
        payload = {
            "model": model or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ServiceUnavailableError(f"Ollama returned HTTP {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("Unable to reach the local Ollama service.") from exc

        body = response.json()
        content = body.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise InvalidLLMResponseError("Ollama returned an empty response.")
        return OllamaChatResult(model=payload["model"], content=content, response_json=body)

    def chat(
        self,
        *,
        prompt: str,
        model: str | None = None,
    ) -> OllamaChatResult:
        payload = {
            "model": model or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0},
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ServiceUnavailableError(f"Ollama returned HTTP {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("Unable to reach the local Ollama service.") from exc

        body = response.json()
        content = body.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise InvalidLLMResponseError("Ollama returned an empty response.")
        return OllamaChatResult(model=payload["model"], content=content, response_json=body)

    def repair_json(
        self,
        *,
        invalid_response: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> OllamaChatResult:
        prompt = (
            "You repair invalid JSON extracted from a brokerage note parser.\n"
            "Return only valid JSON matching this schema.\n"
            f"Schema:\n{json.dumps(schema, ensure_ascii=True)}\n\n"
            "Broken response:\n"
            f"{invalid_response}"
        )
        return self.chat_with_schema(prompt=prompt, schema=schema, model=model)
