from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas.pdf_import import PDFImportReviewPayload
from app.schemas.trade_analytics import TradeAnalyticsSnapshot


class SmartTradeAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class AuthSession:
    access_token: str
    user_email: str
    expires_at: str


class SmartTradeAPIClient:
    def __init__(self, *, base_url: str, timeout_seconds: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def login(self, *, email: str, password: str) -> AuthSession:
        payload = self._post("/auth/login", json={"email": email, "password": password})
        token_data = payload["data"]
        return AuthSession(
            access_token=token_data["access_token"],
            user_email=token_data["user"]["email"],
            expires_at=token_data["expires_at"],
        )

    def review_pdf_import(self, *, file_name: str, file_bytes: bytes, access_token: str) -> PDFImportReviewPayload:
        payload = self._post(
            "/imports/pdf/review",
            headers=self._auth_headers(access_token),
            files={"file": (file_name, file_bytes, "application/pdf")},
        )
        return PDFImportReviewPayload.model_validate(payload["data"])

    def create_trade(self, *, trade_payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        payload = self._post(
            "/trades",
            json=trade_payload,
            headers=self._auth_headers(access_token),
        )
        return payload["data"]

    def create_trades_bulk(self, *, trade_payloads: list[dict[str, Any]], access_token: str) -> dict[str, Any]:
        payload = self._post(
            "/trades/bulk",
            json={"trades": trade_payloads},
            headers=self._auth_headers(access_token),
        )
        return payload["data"]

    def get_trade_analytics(
        self,
        *,
        access_token: str,
        params: dict[str, Any] | None = None,
    ) -> TradeAnalyticsSnapshot:
        payload = self._get(
            "/analytics/trades",
            params=params,
            headers=self._auth_headers(access_token),
        )
        return TradeAnalyticsSnapshot.model_validate(payload["data"])

    def list_trades(
        self,
        *,
        access_token: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._get(
            "/trades",
            params=params,
            headers=self._auth_headers(access_token),
        )
        return payload

    def get_tax_report(self, *, access_token: str) -> dict[str, Any]:
        payload = self._get(
            "/analytics/taxes",
            headers=self._auth_headers(access_token),
        )
        return payload["data"]

    def get_ollama_health(self) -> dict[str, Any]:
        try:
            return self._get("/health/ollama")
        except SmartTradeAPIError:
            return {"reachable": False, "error": "Could not reach backend."}

    def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.get(path, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise SmartTradeAPIError("Nao foi possivel conectar ao backend FastAPI local.") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise SmartTradeAPIError(
                "O backend retornou uma resposta invalida.",
                status_code=response.status_code,
            ) from exc

        if response.is_error:
            raise SmartTradeAPIError(
                body.get("detail", "A requisicao falhou."),
                status_code=response.status_code,
                error_code=body.get("error_code"),
            )
        return body

    def _post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.post(path, json=json, files=files, headers=headers)
        except httpx.HTTPError as exc:
            raise SmartTradeAPIError("Nao foi possivel conectar ao backend FastAPI local.") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise SmartTradeAPIError(
                "O backend retornou uma resposta invalida.",
                status_code=response.status_code,
            ) from exc

        if response.is_error:
            raise SmartTradeAPIError(
                body.get("detail", "A requisicao falhou."),
                status_code=response.status_code,
                error_code=body.get("error_code"),
            )
        return body

    @staticmethod
    def _auth_headers(access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}
