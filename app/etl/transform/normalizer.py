from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC
from decimal import Decimal

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import ETLValidationError
from app.etl.detect.value_parsers import cleanup_ticker
from app.etl.transform.parsers import (
    is_blankish,
    normalize_lookup_text,
    normalize_text,
    parse_decimal,
    parse_reference_date,
    slugify_text,
)


logger = logging.getLogger(__name__)

ZERO_DECIMAL = Decimal("0")
REQUIRED_SOURCE_FIELDS = ("client_name", "broker", "asset_name", "quantity")
REQUIRED_OUTPUT_COLUMNS = (
    "client_name",
    "broker",
    "original_name",
    "normalized_name",
    "ticker",
    "quantity",
    "avg_price",
    "total_value",
    "reference_date",
    "risk_profile",
)

COLUMN_ALIASES: dict[str, set[str]] = {
    "client_name": {
        "cliente",
        "client",
        "investidor",
        "nome cliente",
        "nome do cliente",
        "nome do investidor",
        "titular",
        "nome investidor",
        "account holder",
        "holder",
    },
    "broker": {
        "corretora",
        "instituicao",
        "institution",
        "broker",
        "custodian",
        "instituicao financeira",
        "banco",
        "plataforma",
        "origem",
        "brokerage",
    },
    "asset_name": {
        "ativo",
        "produto",
        "descricao",
        "asset",
        "nome ativo",
        "nome do ativo",
        "descricao do ativo",
        "papel",
        "instrumento",
        "security",
        "asset name",
    },
    "ticker": {
        "ticker",
        "codigo",
        "cod ativo",
        "cod_ativo",
        "symbol",
        "codigo do ativo",
        "asset code",
        "isin",
    },
    "quantity": {
        "qtd",
        "qtde",
        "quantidade",
        "quantity",
        "position",
        "saldo",
        "saldo atual",
        "quantidade disponivel",
        "holding quantity",
    },
    "avg_price": {
        "preco medio",
        "avg price",
        "average price",
        "average_price",
        "preco de compra",
        "preco unitario",
        "pu",
        "cost basis",
    },
    "total_value": {
        "valor total",
        "valor atual",
        "financial value",
        "total value",
        "gross_value",
        "valor bruto",
        "market value",
        "net worth",
        "position value",
    },
    "reference_date": {
        "data referencia",
        "data de referencia",
        "reference_date",
        "date",
        "data posicao",
        "position date",
        "snapshot date",
        "data base",
    },
    "risk_profile": {
        "perfil",
        "perfil risco",
        "risk profile",
        "risk_profile",
        "suitability",
    },
}

ASSET_NAME_ALIASES: dict[str, str] = {
    "BTC": "BITCOIN",
    "BITCOIN": "BITCOIN",
    "ETH": "ETHEREUM",
    "ETHER": "ETHEREUM",
    "ETHEREUM": "ETHEREUM",
    "TESOURO SELIC 2029": "TESOURO SELIC 2029",
}

BROKER_ALIASES: dict[str, str] = {
    "XP INVESTIMENTOS": "XP",
    "XP": "XP",
    "XP INC": "XP",
    "BTG PACTUAL": "BTG",
    "BTG": "BTG",
    "AVENUE SECURITIES": "AVENUE",
    "AVENUE": "AVENUE",
    "ITAU": "ITAU",
    "ITAU CORRETORA": "ITAU",
    "BINANCE": "CRYPTO",
    "MERCADO BITCOIN": "CRYPTO",
    "CRYPTO": "CRYPTO",
}

RISK_PROFILE_ALIASES: dict[str, str] = {
    "CONSERVADOR": "conservador",
    "MODERADO": "moderado",
    "ARROJADO": "arrojado",
    "AGRESSIVO": "arrojado",
}


def resolve_canonical_column(column_name: str) -> str:
    normalized_name = slugify_text(column_name)
    for canonical_name, aliases in COLUMN_ALIASES.items():
        if normalized_name == canonical_name.replace("_", " ") or normalized_name in aliases:
            return canonical_name
    return normalized_name.replace(" ", "_")


def normalize_ticker(value: object) -> str | None:
    if is_blankish(value):
        return None
    return cleanup_ticker(value)


def normalize_asset_name(value: object) -> str:
    text = normalize_lookup_text(value, "UNKNOWN_ASSET")
    return ASSET_NAME_ALIASES.get(text, text)


def normalize_broker_name(value: object) -> str:
    text = normalize_lookup_text(value, "UNKNOWN_BROKER")
    return BROKER_ALIASES.get(text, text)


def normalize_risk_profile(value: object) -> str:
    text = normalize_lookup_text(value, get_settings().default_risk_profile.upper())
    return RISK_PROFILE_ALIASES.get(text, text.lower())


def normalize_portfolio_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        raise ETLValidationError("The input dataset is empty.")

    renamed_columns = {column: resolve_canonical_column(column) for column in dataframe.columns}
    logger.info("Resolved input columns: %s", renamed_columns)
    frame = dataframe.rename(columns=renamed_columns).copy()
    logger.info("Detected canonicalized portfolio columns: %s", list(frame.columns))

    frame = _apply_missing_column_fallbacks(frame)
    _validate_required_source_columns(frame)
    frame = _build_default_columns(frame)
    frame = _fill_missing_broker_values(frame)

    frame["client_name"] = frame["client_name"].map(lambda value: normalize_text(value, "Unknown Client"))
    frame["broker"] = frame["broker"].map(normalize_broker_name)
    frame["original_name"] = frame["asset_name"].map(lambda value: normalize_text(value, "Unknown Asset"))
    frame["normalized_name"] = frame["asset_name"].map(normalize_asset_name)
    frame["ticker"] = frame["ticker"].map(normalize_ticker)
    frame["risk_profile"] = frame["risk_profile"].map(normalize_risk_profile)
    frame["quantity"] = frame["quantity"].map(parse_decimal)
    frame["avg_price"] = frame["avg_price"].map(parse_decimal)
    frame["total_value"] = frame["total_value"].map(parse_decimal)
    frame["reference_date"] = frame["reference_date"].map(parse_reference_date)

    missing_reference_dates = frame["reference_date"].isna()
    if missing_reference_dates.any():
        fallback_reference_date = _get_default_reference_date()
        logger.warning(
            "Filled %s rows with fallback reference date %s.",
            int(missing_reference_dates.sum()),
            fallback_reference_date,
        )
        frame.loc[missing_reference_dates, "reference_date"] = fallback_reference_date

    _derive_financial_values(frame)
    frame, rows_skipped, validation_summary = _drop_invalid_rows(frame)
    if frame.empty:
        summary_text = _format_validation_summary(validation_summary)
        raise ETLValidationError(f"No valid portfolio rows were found after normalization. {summary_text}")

    normalized = frame[list(REQUIRED_OUTPUT_COLUMNS)].copy()
    normalized.attrs["rows_skipped"] = rows_skipped
    normalized.attrs["validation_summary"] = dict(validation_summary)
    normalized.attrs["review_required"] = bool(frame.attrs.get("review_required", False))
    normalized.attrs["review_reasons"] = tuple(frame.attrs.get("review_reasons", ()))
    normalized.attrs["inferred_fields"] = dict(frame.attrs.get("inferred_fields", {}))
    normalized.attrs["normalization_warnings"] = tuple(frame.attrs.get("normalization_warnings", ()))
    return normalized


def _validate_required_source_columns(frame: pd.DataFrame) -> None:
    missing_fields = [field for field in REQUIRED_SOURCE_FIELDS if field not in frame.columns]
    if not missing_fields:
        return

    available_columns = ", ".join(sorted(frame.columns))
    suggestions = _build_missing_column_suggestions(missing_fields)
    example_fix = (
        "Example fix: add a 'Corretora'/'Broker' column, or include a recognizable source hint such as 'XP' or "
        "'BTG' in the filename so the broker can be inferred."
        if "broker" in missing_fields
        else "Example fix: rename the source columns to the canonical portfolio headers or add the missing fields."
    )
    raise ETLValidationError(
        "Missing required portfolio columns after alias resolution: "
        f"{', '.join(missing_fields)}. Available columns: {available_columns}. "
        f"Suggested mapping: {suggestions}. {example_fix}"
    )


def _apply_missing_column_fallbacks(frame: pd.DataFrame) -> pd.DataFrame:
    settings = get_settings()
    inferred_fields = dict(frame.attrs.get("inferred_fields", {}))
    review_reasons = list(frame.attrs.get("review_reasons", ()))
    normalization_warnings = list(frame.attrs.get("normalization_warnings", ()))

    missing_fields = [field for field in REQUIRED_SOURCE_FIELDS if field not in frame.columns]
    if not missing_fields:
        return frame

    logger.warning("Required portfolio columns missing after alias resolution: %s", missing_fields)

    if "broker" in missing_fields and settings.infer_missing_broker:
        inferred_broker, inference_source = _infer_broker_value(frame)
        if inferred_broker is not None:
            frame["broker"] = inferred_broker
            inferred_fields["broker"] = inference_source
            review_reasons.append("broker_inferred")
            normalization_warnings.append(f"broker inferred from {inference_source}")
            logger.warning(
                "Missing broker column inferred as '%s' using %s.",
                inferred_broker,
                inference_source,
            )
        elif settings.etl_soft_validation_mode:
            frame["broker"] = settings.default_broker_name
            inferred_fields["broker"] = "default_unknown"
            review_reasons.append("broker_defaulted_unknown")
            normalization_warnings.append("broker defaulted to UNKNOWN because no reliable hint was found")
            logger.warning(
                "Missing broker column defaulted to '%s' because no reliable hint was found.",
                settings.default_broker_name,
            )

    frame.attrs["inferred_fields"] = inferred_fields
    frame.attrs["normalization_warnings"] = tuple(normalization_warnings)
    if review_reasons:
        frame.attrs["review_required"] = True
        frame.attrs["review_reasons"] = tuple(dict.fromkeys(review_reasons))
    return frame


def _build_default_columns(frame: pd.DataFrame) -> pd.DataFrame:
    settings = get_settings()
    defaults = {
        "ticker": None,
        "avg_price": None,
        "total_value": None,
        "reference_date": _get_default_reference_date().isoformat(),
        "risk_profile": settings.default_risk_profile,
    }
    for column, default_value in defaults.items():
        if column not in frame.columns:
            frame[column] = default_value
            logger.info("Applied default value for missing column '%s'.", column)
    return frame


def _fill_missing_broker_values(frame: pd.DataFrame) -> pd.DataFrame:
    if "broker" not in frame.columns:
        return frame

    settings = get_settings()
    missing_broker_mask = frame["broker"].map(is_blankish)
    if not missing_broker_mask.any():
        return frame

    inferred_broker, inference_source = _infer_broker_value(frame)
    replacement_value = inferred_broker or settings.default_broker_name
    frame.loc[missing_broker_mask, "broker"] = replacement_value

    review_reasons = list(frame.attrs.get("review_reasons", ()))
    normalization_warnings = list(frame.attrs.get("normalization_warnings", ()))
    inferred_fields = dict(frame.attrs.get("inferred_fields", {}))

    if inferred_broker is not None:
        review_reasons.append("broker_inferred")
        normalization_warnings.append(f"broker filled from {inference_source}")
        inferred_fields["broker"] = inference_source
        logger.warning(
            "Filled %s blank broker values with inferred broker '%s' from %s.",
            int(missing_broker_mask.sum()),
            inferred_broker,
            inference_source,
        )
    else:
        review_reasons.append("broker_defaulted_unknown")
        normalization_warnings.append("broker blank values defaulted to UNKNOWN")
        inferred_fields["broker"] = "default_unknown"
        logger.warning(
            "Filled %s blank broker values with default broker '%s'.",
            int(missing_broker_mask.sum()),
            settings.default_broker_name,
        )

    frame.attrs["review_required"] = True
    frame.attrs["review_reasons"] = tuple(dict.fromkeys(review_reasons))
    frame.attrs["normalization_warnings"] = tuple(normalization_warnings)
    frame.attrs["inferred_fields"] = inferred_fields
    return frame


def _derive_financial_values(frame: pd.DataFrame) -> None:
    missing_total_value = frame["total_value"].isna() & frame["quantity"].notna() & frame["avg_price"].notna()
    frame.loc[missing_total_value, "total_value"] = frame.loc[missing_total_value].apply(
        lambda row: row["quantity"] * row["avg_price"],
        axis=1,
    )

    missing_avg_price = (
        frame["avg_price"].isna()
        & frame["quantity"].notna()
        & frame["quantity"].ne(ZERO_DECIMAL)
        & frame["total_value"].notna()
    )
    frame.loc[missing_avg_price, "avg_price"] = frame.loc[missing_avg_price].apply(
        lambda row: row["total_value"] / row["quantity"],
        axis=1,
    )

    frame["avg_price"] = frame["avg_price"].map(lambda value: value if value is not None else ZERO_DECIMAL)
    frame["total_value"] = frame["total_value"].map(lambda value: value if value is not None else ZERO_DECIMAL)


def _drop_invalid_rows(frame: pd.DataFrame) -> tuple[pd.DataFrame, int, Counter[str]]:
    frame_attrs = dict(frame.attrs)
    validation_rules = {
        "missing_client_name": frame["client_name"].eq("Unknown Client"),
        "missing_broker": frame["broker"].eq("UNKNOWN_BROKER"),
        "missing_asset_name": frame["normalized_name"].eq("UNKNOWN_ASSET"),
        "invalid_quantity": frame["quantity"].isna() | frame["quantity"].lt(ZERO_DECIMAL),
        "invalid_avg_price": frame["avg_price"].lt(ZERO_DECIMAL),
        "invalid_total_value": frame["total_value"].lt(ZERO_DECIMAL),
        "missing_reference_date": frame["reference_date"].isna(),
    }

    invalid_mask = pd.Series(False, index=frame.index)
    validation_summary: Counter[str] = Counter()

    for reason, mask in validation_rules.items():
        count = int(mask.sum())
        if count:
            validation_summary[reason] += count
            invalid_mask = invalid_mask | mask

    invalid_row_count = int(invalid_mask.sum())
    cleaned = frame.loc[~invalid_mask].copy()
    cleaned.attrs.update(frame_attrs)
    if validation_summary:
        logger.warning("Dropped %s invalid rows. Reasons: %s", invalid_row_count, dict(validation_summary))
    return cleaned, invalid_row_count, validation_summary


def _format_validation_summary(summary: Counter[str]) -> str:
    if not summary:
        return ""
    return "Validation summary: " + ", ".join(f"{reason}={count}" for reason, count in sorted(summary.items()))


def _get_default_reference_date():
    return pd.Timestamp.now(tz=UTC).date()


def _infer_broker_value(frame: pd.DataFrame) -> tuple[str | None, str]:
    for column in ("broker", "custodian", "institution", "instituicao", "instituicao_financeira", "corretora"):
        if column not in frame.columns:
            continue
        candidate = _pick_broker_candidate(frame[column])
        if candidate is not None:
            return candidate, f"column:{column}"

    for column in ("advisorcode", "advisor_code", "advisor", "assessor", "codigo_assessor", "advisor code"):
        if column not in frame.columns:
            continue
        advisor_values = [str(value) for value in frame[column].tolist() if not is_blankish(value)]
        if advisor_values:
            filename_candidate = _infer_broker_from_text(str(frame.attrs.get("source_filename", "")))
            if filename_candidate is not None:
                return filename_candidate, f"filename+{column}"

    source_hints = [
        str(frame.attrs.get("source_filename", "")),
        str(frame.attrs.get("source_path", "")),
        str(frame.attrs.get("parser_name", "")),
    ]
    for hint in source_hints:
        candidate = _infer_broker_from_text(hint)
        if candidate is not None:
            return candidate, "source_metadata"

    return None, "unresolved"


def _pick_broker_candidate(series: pd.Series) -> str | None:
    for value in series.tolist():
        candidate = _infer_broker_from_text(str(value))
        if candidate is not None:
            return candidate
    return None


def _infer_broker_from_text(value: str) -> str | None:
    normalized_value = normalize_lookup_text(value, "")
    if not normalized_value:
        return None

    if normalized_value in BROKER_ALIASES:
        return BROKER_ALIASES[normalized_value]

    for alias, canonical_name in BROKER_ALIASES.items():
        if alias and alias in normalized_value:
            return canonical_name
    return None


def _build_missing_column_suggestions(missing_fields: list[str]) -> str:
    suggestions: list[str] = []
    if "broker" in missing_fields:
        suggestions.append("custodian/institution/corretora -> broker")
    if "client_name" in missing_fields:
        suggestions.append("cliente/client/investidor -> client_name")
    if "asset_name" in missing_fields:
        suggestions.append("ativo/asset/descricao -> asset_name")
    if "quantity" in missing_fields:
        suggestions.append("qtd/qtde/quantidade -> quantity")
    return "; ".join(suggestions) or "Review the source headers and map them to the canonical portfolio fields"
