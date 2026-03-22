from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import APIResponse


router = APIRouter()


def _fetch_ollama_tags(base_url: str, timeout: int) -> tuple[bool, list[str], str | None]:
    """Returns (reachable, model_names, error_message)."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{base_url}/api/tags")
            response.raise_for_status()
        data = response.json()
        names = [m.get("name", "") for m in data.get("models", [])]
        return True, names, None
    except httpx.HTTPError as exc:
        return False, [], str(exc)


@router.get("/health/ollama", tags=["health"])
def ollama_health() -> dict[str, Any]:
    settings = get_settings()
    reachable, available_models, error = _fetch_ollama_tags(
        settings.ollama_base_url, min(settings.ollama_timeout_seconds, 10)
    )
    configured_model = settings.ollama_model
    model_available = configured_model in available_models if reachable else False
    return {
        "reachable": reachable,
        "configured_model": configured_model,
        "model_available": model_available,
        "available_models": available_models,
        "base_url": settings.ollama_base_url,
        "error": error,
    }
