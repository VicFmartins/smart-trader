from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from app.core.exceptions import ETLInputError
from app.etl.extract.xp_common import (
    XP_BROKER_NAME,
    parse_date_from_filename,
    rename_columns_by_alias,
    sanitize_client_name,
    select_excel_table,
)


logger = logging.getLogger(__name__)

POSITION_COLUMN_ALIASES: dict[str, set[str]] = {
    "client_name": {"cliente", "investidor", "titular", "nome cliente", "nome do cliente", "nome investidor"},
    "client_id": {"clientid"},
    "asset_name": {"produto", "ativo", "descricao", "descrição", "produto ativo", "nome do ativo", "asset"},
    "ticker": {"ticker", "codigo", "código", "codigo do ativo", "cod ativo", "sigla", "cetipseliccode"},
    "quantity": {"quantidade", "qtd", "saldo", "saldo atual", "posição", "posicao", "quantidade disponivel", "closingquantity"},
    "avg_price": {"preco medio", "preço médio", "pm", "preco unitario", "preço unitário", "closingunitprice"},
    "total_value": {"valor", "valor total", "valor financeiro", "financeiro", "valor bruto", "saldo financeiro", "closingvalue"},
    "reference_date": {"data", "data posicao", "data posição", "data da posicao", "data da posição", "effectivedate"},
    "risk_profile": {"perfil", "perfil risco", "suitability"},
    "asset_id": {"assetid"},
    "market_type": {"markettype"},
    "fund_cnpj": {"fundcnpj"},
    "maturity_date": {"duedate"},
    "isin_code": {"isin"},
    "issuer_name": {"issuer"},
}


class XPPositionParser:
    name = "xp_position_parser"

    def parse(self, file_path: Path) -> pd.DataFrame:
        frame = select_excel_table(file_path, POSITION_COLUMN_ALIASES)
        frame = rename_columns_by_alias(frame, POSITION_COLUMN_ALIASES)
        frame = self._collapse_to_latest_snapshot(frame)
        frame["broker"] = XP_BROKER_NAME

        if "client_name" not in frame.columns:
            if "client_id" in frame.columns:
                frame["client_name"] = frame["client_id"].map(lambda value: sanitize_client_name(f"XP Client {value}"))
                logger.warning("XP position file %s did not provide a client name column. Using clientId-based fallback.", file_path)
            else:
                frame["client_name"] = sanitize_client_name(None)
                logger.warning("XP position file %s did not provide a client name column. Using fallback value.", file_path)
        else:
            frame["client_name"] = frame["client_name"].map(sanitize_client_name)

        if "reference_date" not in frame.columns:
            inferred_reference_date = parse_date_from_filename(file_path)
            if inferred_reference_date is not None:
                frame["reference_date"] = inferred_reference_date.isoformat()
            else:
                logger.warning(
                    "XP position file %s did not provide a reference date column and no date was inferred from the filename.",
                    file_path,
                )

        missing = [column for column in ("asset_name", "quantity") if column not in frame.columns]
        if missing:
            raise ETLInputError(
                f"XP position file is missing required columns after parsing: {', '.join(missing)}. File: {file_path}"
            )

        logger.info("Parsed XP position workbook %s using %s", file_path, self.name)
        return frame.reset_index(drop=True)

    def _collapse_to_latest_snapshot(self, frame: pd.DataFrame) -> pd.DataFrame:
        working = frame.copy()
        if "asset_name" not in working.columns and "asset" in working.columns:
            working["asset_name"] = working["asset"]
        if "ticker" not in working.columns:
            if "cetipSelicCode" in working.columns:
                working["ticker"] = working["cetipSelicCode"]
            elif "isin_code" in working.columns:
                working["ticker"] = working["isin_code"]
            else:
                working["ticker"] = None
        if "quantity" not in working.columns and "closingQuantity" in working.columns:
            working["quantity"] = working["closingQuantity"]
        if "avg_price" not in working.columns and "closingUnitPrice" in working.columns:
            working["avg_price"] = working["closingUnitPrice"]
        if "total_value" not in working.columns and "closingValue" in working.columns:
            working["total_value"] = working["closingValue"]
        if "reference_date" not in working.columns and "effectiveDate" in working.columns:
            working["reference_date"] = working["effectiveDate"]
        if "risk_profile" not in working.columns:
            working["risk_profile"] = None

        sort_columns = [column for column in ("reference_date", "effectiveDate") if column in working.columns]
        if sort_columns:
            working = working.sort_values(by=sort_columns)

        group_keys = [column for column in ("asset_id", "asset_name", "ticker") if column in working.columns]
        if not group_keys:
            return working

        latest = working.groupby(group_keys, dropna=False, as_index=False).tail(1).copy()
        return latest.loc[latest["quantity"].notna()].copy()
