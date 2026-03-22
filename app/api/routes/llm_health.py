from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter

from app.core.config import get_settings
from app.api.routes.ollama_health import _fetch_ollama_tags


router = APIRouter()


@router.get("/health/llm", tags=["health"])
def llm_health() -> dict[str, Any]:
    """Provider-aware LLM health check.

    Reports the active provider (ollama or gemini), whether it is reachable,
    and whether the configured model is available.
    """
    settings = get_settings()
    if settings.llm_provider == "gemini":
        return _check_gemini(settings)
    return _check_ollama(settings)


# ---------------------------------------------------------------------------
# Provider-specific checks
# ---------------------------------------------------------------------------


def _check_ollama(settings) -> dict[str, Any]:
    reachable, available_models, error = _fetch_ollama_tags(
        settings.ollama_base_url, min(settings.ollama_timeout_seconds, 10)
    )
    configured_model = settings.ollama_model
    return {
        "provider": "ollama",
        "reachable": reachable,
        "configured_model": configured_model,
        "model_available": configured_model in available_models if reachable else False,
        "available_models": available_models,
        "base_url": settings.ollama_base_url,
        "error": error,
    }


def _check_gemini(settings) -> dict[str, Any]:
    configured_model = settings.gemini_model
    if not settings.gemini_api_key:
        return {
            "provider": "gemini",
            "reachable": False,
            "configured_model": configured_model,
            "model_available": False,
            "available_models": [],
            "base_url": "https://generativelanguage.googleapis.com",
            "error": "GEMINI_API_KEY is not configured.",
        }

    url = "https://generativelanguage.googleapis.com/v1beta/models"
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params={"key": settings.gemini_api_key})
            response.raise_for_status()
        raw_models = response.json().get("models", [])
        available_models = [m.get("name", "").removeprefix("models/") for m in raw_models]
        model_available = configured_model in available_models
        return {
            "provider": "gemini",
            "reachable": True,
            "configured_model": configured_model,
            "model_available": model_available,
            "available_models": available_models,
            "base_url": "https://generativelanguage.googleapis.com",
            "error": None,
        }
    except httpx.HTTPStatusError as exc:
        return {
            "provider": "gemini",
            "reachable": False,
            "configured_model": configured_model,
            "model_available": False,
            "available_models": [],
            "base_url": "https://generativelanguage.googleapis.com",
            "error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
        }
    except httpx.HTTPError as exc:
        return {
            "provider": "gemini",
            "reachable": False,
            "configured_model": configured_model,
            "model_available": False,
            "available_models": [],
            "base_url": "https://generativelanguage.googleapis.com",
            "error": str(exc),
        }
