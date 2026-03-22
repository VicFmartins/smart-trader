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
from app.etl.transform.parsers import parse_decimal, parse_reference_date


logger = logging.getLogger(__name__)

MOVEMENT_COLUMN_ALIASES: dict[str, set[str]] = {
    "client_name": {"cliente", "investidor", "titular", "nome cliente", "nome do cliente", "nome investidor"},
    "client_id": {"clientid"},
    "asset_name": {"produto", "ativo", "descricao", "descrição", "produto ativo", "nome do ativo", "asset"},
    "ticker": {"ticker", "codigo", "código", "codigo do ativo", "cod ativo", "sigla", "isin"},
    "quantity": {"quantidade", "qtd", "quantidade movimentada", "qtd movimentada"},
    "avg_price": {"preco unitario", "preço unitário", "preco medio", "preço médio", "valor unitario", "unitprice", "price"},
    "total_value": {"valor", "valor liquido", "valor líquido", "financeiro", "valor financeiro", "valor da operacao", "grossvalue", "netvalue"},
    "movement_type": {"movimentacao", "movimentação", "tipo", "tipo de movimento", "historico", "histórico", "operacao", "operação", "eventtype", "type"},
    "reference_date": {"data", "data movimento", "data movimentacao", "data movimentação", "effectivedate", "operationdate", "settlementdate"},
    "risk_profile": {"perfil", "perfil risco", "suitability"},
    "asset_classification": {"assetclassification"},
}

POSITIVE_MOVEMENTS = ("compra", "purchase", "aplicacao", "aplicação", "entrada", "bonificacao", "bonificação", "transferencia entrada")
NEGATIVE_MOVEMENTS = ("venda", "sale", "resgate", "saida", "saída", "transferencia saida", "transferência saída")


class XPMovementsParser:
    name = "xp_movements_parser"

    def parse(self, file_path: Path) -> pd.DataFrame:
        frame = select_excel_table(file_path, MOVEMENT_COLUMN_ALIASES)
        frame = rename_columns_by_alias(frame, MOVEMENT_COLUMN_ALIASES)
        frame["broker"] = XP_BROKER_NAME
        if "ticker" not in frame.columns:
            frame["ticker"] = None
        if "risk_profile" not in frame.columns:
            frame["risk_profile"] = None

        if "client_name" not in frame.columns:
            if "client_id" in frame.columns:
                frame["client_name"] = frame["client_id"].map(lambda value: sanitize_client_name(f"XP Client {value}"))
                logger.warning("XP movements file %s did not provide a client name column. Using clientId-based fallback.", file_path)
            else:
                frame["client_name"] = sanitize_client_name(None)
                logger.warning("XP movements file %s did not provide a client name column. Using fallback value.", file_path)
        else:
            frame["client_name"] = frame["client_name"].map(sanitize_client_name)

        if "reference_date" not in frame.columns:
            inferred_reference_date = parse_date_from_filename(file_path)
            if inferred_reference_date is not None:
                frame["reference_date"] = inferred_reference_date.isoformat()
            else:
                frame["reference_date"] = None

        missing = [column for column in ("asset_name", "quantity", "movement_type") if column not in frame.columns]
        if missing:
            raise ETLInputError(
                f"XP movements file is missing required columns after parsing: {', '.join(missing)}. File: {file_path}"
            )

        aggregated = self._aggregate_movements(frame, file_path)
        logger.info("Parsed XP movements workbook %s using %s", file_path, self.name)
        return aggregated.reset_index(drop=True)

    def _aggregate_movements(self, frame: pd.DataFrame, file_path: Path) -> pd.DataFrame:
        working = frame.copy()
        working["parsed_quantity"] = working["quantity"].map(parse_decimal)
        if "avg_price" in working.columns:
            working["parsed_avg_price"] = working["avg_price"].map(parse_decimal)
        else:
            working["parsed_avg_price"] = None
        if "total_value" in working.columns:
            working["parsed_total_value"] = working["total_value"].map(parse_decimal)
        else:
            working["parsed_total_value"] = None
        working["parsed_reference_date"] = working["reference_date"].map(parse_reference_date)
        working["movement_sign"] = working["movement_type"].map(self._resolve_movement_sign)
        if "asset_classification" in working.columns:
            cash_like_mask = working["asset_classification"].astype(str).str.upper().eq("CAIXA")
            working = working.loc[~cash_like_mask].copy()

        valid_mask = working["parsed_quantity"].notna() & working["movement_sign"].notna()
        skipped_rows = int((~valid_mask).sum())
        if skipped_rows:
            logger.warning(
                "Skipped %s XP movement rows from %s because quantity or movement type could not be interpreted.",
                skipped_rows,
                file_path,
            )
        working = working.loc[valid_mask].copy()
        working["movement_sign"] = working["movement_sign"].astype(int)
        if working.empty:
            raise ETLInputError(f"XP movements file did not produce any position-like rows after aggregation: {file_path}")

        working["signed_quantity"] = working["parsed_quantity"] * working["movement_sign"]
        working["base_value"] = working["parsed_total_value"]
        missing_value = working["base_value"].isna() & working["parsed_avg_price"].notna()
        working.loc[missing_value, "base_value"] = (
            working.loc[missing_value, "parsed_quantity"] * working.loc[missing_value, "parsed_avg_price"]
        )
        working["base_value"] = working["base_value"].fillna(0)
        working["positive_quantity_component"] = working.apply(
            lambda row: row["parsed_quantity"] if row["movement_sign"] > 0 else 0,
            axis=1,
        )
        working["positive_value_component"] = working.apply(
            lambda row: row["base_value"] if row["movement_sign"] > 0 else 0,
            axis=1,
        )

        grouped = (
            working.groupby(["client_name", "broker", "asset_name", "ticker", "risk_profile"], dropna=False)
            .agg(
                net_quantity=("signed_quantity", "sum"),
                positive_quantity=("positive_quantity_component", "sum"),
                positive_value=("positive_value_component", "sum"),
                reference_date=("parsed_reference_date", "max"),
            )
            .reset_index()
        )

        grouped = grouped.loc[grouped["net_quantity"].notna() & grouped["net_quantity"].gt(0)].copy()
        if grouped.empty:
            raise ETLInputError(
                f"XP movements file only produced zero or negative net quantities, so no open positions were inferred: {file_path}"
            )

        grouped["avg_price"] = grouped.apply(
            lambda row: (row["positive_value"] / row["positive_quantity"]) if row["positive_quantity"] else None,
            axis=1,
        )
        grouped["total_value"] = grouped.apply(
            lambda row: (row["avg_price"] * row["net_quantity"]) if row["avg_price"] is not None else None,
            axis=1,
        )
        grouped["quantity"] = grouped["net_quantity"]
        grouped["reference_date"] = grouped["reference_date"].map(
            lambda value: value.isoformat() if pd.notna(value) and value is not None else None
        )

        return grouped[
            ["client_name", "broker", "asset_name", "ticker", "quantity", "avg_price", "total_value", "reference_date", "risk_profile"]
        ]

    def _resolve_movement_sign(self, value: object) -> int | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip().lower()
        if any(keyword in text for keyword in POSITIVE_MOVEMENTS):
            return 1
        if any(keyword in text for keyword in NEGATIVE_MOVEMENTS):
            return -1
        return None
