from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.exceptions import ETLInputError
from app.etl.extract.xp_common import XP_BROKER_NAME, load_json_payload, parse_date_from_filename, sanitize_client_name

JSON_COLUMN_ALIASES = {
    "client_name": ("client_name", "cliente", "investidor", "titular", "holder_name"),
    "client_id": ("clientid",),
    "asset_name": ("asset_name", "ativo", "produto", "descricao", "description", "name", "asset"),
    "ticker": ("ticker", "symbol", "codigo", "code", "cetipseliccode", "isin"),
    "quantity": ("quantity", "qtd", "quantidade", "position", "closingquantity"),
    "avg_price": ("avg_price", "average_price", "preco_medio", "preco medio", "price", "closingunitprice"),
    "total_value": ("total_value", "market_value", "valor_total", "valor total", "financial_value", "closingvalue"),
    "reference_date": ("reference_date", "data", "position_date", "snapshot_date", "effectivedate"),
    "risk_profile": ("risk_profile", "perfil", "suitability"),
}


class XPJsonParser:
    name = "xp_json_parser"

    def parse(self, file_path: Path) -> pd.DataFrame:
        payload = load_json_payload(file_path)
        records = self._collect_records(payload)
        if not records:
            raise ETLInputError(f"XP JSON file did not contain a usable list of position records: {file_path}")

        normalized_records = [self._normalize_record(record, file_path) for record in records]
        frame = pd.DataFrame(normalized_records)
        frame = frame.dropna(how="all").dropna(axis=1, how="all")
        if frame.empty:
            raise ETLInputError(f"XP JSON file did not produce usable rows after normalization: {file_path}")

        return frame.reset_index(drop=True)

    def _normalize_record(self, record: dict, file_path: Path) -> dict[str, object]:
        normalized: dict[str, object] = {"broker": XP_BROKER_NAME}
        lowered = {str(key).lower(): value for key, value in record.items()}
        for canonical_name, candidate_keys in JSON_COLUMN_ALIASES.items():
            normalized[canonical_name] = next((lowered[key.lower()] for key in candidate_keys if key.lower() in lowered), None)

        if normalized.get("client_name") is None and normalized.get("client_id") is not None:
            normalized["client_name"] = sanitize_client_name(f"XP Client {normalized['client_id']}")
        else:
            normalized["client_name"] = sanitize_client_name(normalized.get("client_name"))
        if normalized.get("reference_date") is None:
            inferred_reference_date = parse_date_from_filename(file_path)
            if inferred_reference_date is not None:
                normalized["reference_date"] = inferred_reference_date.isoformat()
        return normalized

    def _collect_records(self, payload) -> list[dict]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        records: list[dict] = []
        for value in payload.values():
            if isinstance(value, list):
                records.extend(item for item in value if isinstance(item, dict))
        return records
