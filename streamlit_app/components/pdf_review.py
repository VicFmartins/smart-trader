from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
import streamlit as st

from app.schemas.pdf_import import PDFAssetClassification, PDFImportReviewPayload, ReviewableTrade, ReviewWarningSeverity
from streamlit_app.style import (
    SURFACE_LOW, SURFACE, PRIMARY, TERTIARY, ERROR,
    ON_SURFACE, ON_SURFACE_VAR, OUTLINE, PRIMARY_CONT,
    section_header,
)


EDITABLE_COLUMNS = [
    "selected",
    "trade_date",
    "trade_time",
    "asset_ticker",
    "asset_classification",
    "operation_type",
    "quantity",
    "entry_price",
    "exit_price",
    "gross_result",
    "fees",
    "net_result",
    "broker",
    "notes",
    "confidence_score",
    "source_page",
]


# ── Summary KPI row ────────────────────────────────────────────────────────────
def render_review_summary(payload: PDFImportReviewPayload) -> None:
    ready_count   = sum(1 for t in payload.trades if t.ready_for_persistence)
    blocked_count = sum(1 for t in payload.trades if t.rejection_reasons)
    warning_count = sum(len(t.warnings) for t in payload.trades) + len(payload.warnings)
    broker_label  = payload.normalized_broker or "Não identificada"

    total_color   = ON_SURFACE
    ready_color   = TERTIARY if ready_count > 0 else ON_SURFACE_VAR
    blocked_color = ERROR if blocked_count > 0 else ON_SURFACE_VAR
    warn_color    = "#f4c542" if warning_count > 0 else ON_SURFACE_VAR  # amber

    cols = st.columns(5, gap="small")
    _summary_card(cols[0], "Extraídos",        str(len(payload.trades)), value_color=total_color)
    _summary_card(cols[1], "Prontos",          str(ready_count),         value_color=ready_color)
    _summary_card(cols[2], "Com bloqueios",    str(blocked_count),       value_color=blocked_color)
    _summary_card(cols[3], "Avisos",           str(warning_count),       value_color=warn_color)
    _summary_card(cols[4], "Corretora",        broker_label)

    if blocked_count > 0:
        st.markdown(
            f"""
            <div style="background:rgba(255,180,171,0.07);border:1px solid rgba(255,180,171,0.25);
                        border-radius:2px;padding:0.75rem 1rem;margin-top:0.75rem;
                        display:flex;align-items:center;gap:0.6rem;">
                <span style="font-size:0.9rem;">⚠</span>
                <p style="font-family:'Inter',sans-serif;font-size:0.82rem;
                          color:{ERROR};margin:0;">
                    <strong>{blocked_count} trade(s)</strong> com campos obrigatórios ausentes —
                    edite as colunas na tabela abaixo e marque "Salvar" quando prontos.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Detalhes da extração", expanded=False):
        meta = {
            "arquivo":          payload.filename,
            "batch_id":         payload.import_job.batch_id if payload.import_job else None,
            "data_detectada":   payload.normalized_trade_date.isoformat() if payload.normalized_trade_date else None,
            "modelo LLM":       payload.llm.model,
            "json_válido":      payload.llm.json_valid,
            "fallback_json":    payload.llm.fallback_used,
            "páginas":          payload.extraction.page_count,
            "texto_truncado":   payload.extraction.text_truncated,
        }
        st.json(meta)


# ── Editable trade table ───────────────────────────────────────────────────────
def review_payload_to_dataframe(payload: PDFImportReviewPayload) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for trade in payload.trades:
        rows.append(
            {
                "selected":              trade.ready_for_persistence,
                "trade_index":           trade.trade_index,
                "trade_date":            trade.trade_date.isoformat() if trade.trade_date else "",
                "trade_time":            trade.trade_time or "",
                "asset_ticker":          trade.asset_ticker or "",
                "asset_classification":  trade.asset_classification.value,
                "operation_type":        trade.operation_type or "",
                "quantity":              trade.quantity,
                "entry_price":           _decimal_to_string(trade.entry_price),
                "exit_price":            _decimal_to_string(trade.exit_price),
                "gross_result":          _decimal_to_string(trade.gross_result),
                "fees":                  _decimal_to_string(trade.fees),
                "net_result":            _decimal_to_string(trade.net_result),
                "broker":                trade.broker or "",
                "notes":                 trade.notes or "",
                "confidence_score":      trade.confidence_score,
                "source_page":           trade.source_page,
                "ready_for_persistence": trade.ready_for_persistence,
                "row_warnings":          " | ".join(w.message for w in trade.warnings),
                "rejection_reasons":     " | ".join(trade.rejection_reasons),
            }
        )
    return pd.DataFrame(rows)


def render_editable_trade_table(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        st.markdown(
            f"""
            <div style="background:{SURFACE_LOW};border:1px solid {OUTLINE};border-radius:2px;
                        padding:2rem;text-align:center;">
                <p style="font-family:'Inter',sans-serif;font-size:0.85rem;
                          color:{ON_SURFACE_VAR};margin:0;">
                    Nenhum trade foi encontrado nesse PDF.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return dataframe

    edited = st.data_editor(
        dataframe,
        key="pdf_trade_editor",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "selected":              st.column_config.CheckboxColumn("Salvar",  help="Marque as linhas que devem ser salvas."),
            "trade_index":           st.column_config.NumberColumn("Linha",     disabled=True),
            "trade_date":            st.column_config.TextColumn("Data",        help="YYYY-MM-DD"),
            "trade_time":            st.column_config.TextColumn("Hora",        help="HH:MM:SS"),
            "asset_ticker":          st.column_config.TextColumn("Ticker"),
            "asset_classification":  st.column_config.SelectboxColumn("Classe", options=[i.value for i in PDFAssetClassification]),
            "operation_type":        st.column_config.SelectboxColumn("Lado",   options=["buy", "sell", ""]),
            "quantity":              st.column_config.NumberColumn("Qtd",       step=1, min_value=1),
            "entry_price":           st.column_config.TextColumn("Entrada"),
            "exit_price":            st.column_config.TextColumn("Saída"),
            "gross_result":          st.column_config.TextColumn("Bruto"),
            "fees":                  st.column_config.TextColumn("Custos"),
            "net_result":            st.column_config.TextColumn("Líquido"),
            "broker":                st.column_config.TextColumn("Corretora"),
            "notes":                 st.column_config.TextColumn("Observações"),
            "confidence_score":      st.column_config.NumberColumn("Confiança", min_value=0.0, max_value=1.0, step=0.01),
            "source_page":           st.column_config.NumberColumn("Pág",       step=1, min_value=1),
            "ready_for_persistence": st.column_config.CheckboxColumn("Pronta",  disabled=True),
            "row_warnings":          st.column_config.TextColumn("Avisos",      disabled=True, width="large"),
            "rejection_reasons":     st.column_config.TextColumn("Bloqueios",   disabled=True, width="large"),
        },
        disabled=["trade_index", "ready_for_persistence", "row_warnings", "rejection_reasons"],
        use_container_width=True,
        column_order=EDITABLE_COLUMNS + ["ready_for_persistence", "row_warnings", "rejection_reasons"],
    )
    return edited


# ── Global extraction warnings ─────────────────────────────────────────────────
def render_global_warnings(payload: PDFImportReviewPayload) -> None:
    if not payload.warnings and not payload.validation_errors:
        return

    section_header("Avisos da Extração")
    for warning in payload.warnings:
        if warning.severity == ReviewWarningSeverity.ERROR:
            st.error(warning.message)
        else:
            st.warning(warning.message)

    for message in payload.validation_errors:
        st.error(message)


# ── Save results ───────────────────────────────────────────────────────────────
def render_save_results(saved_rows: list[dict[str, Any]], save_errors: list[str]) -> None:
    if saved_rows:
        st.markdown(
            f"""
            <div style="background:rgba(47,217,244,0.06);border:1px solid rgba(47,217,244,0.25);
                        border-radius:2px;padding:0.75rem 1rem;margin-top:0.5rem;
                        display:flex;align-items:center;gap:0.6rem;">
                <span style="font-size:0.9rem;">✓</span>
                <p style="font-family:'Inter',sans-serif;font-size:0.85rem;
                          color:{TERTIARY};margin:0;font-weight:600;">
                    {len(saved_rows)} trade(s) salvos com sucesso.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Trades salvos", expanded=False):
            st.dataframe(pd.DataFrame(saved_rows), use_container_width=True, hide_index=True)

    if save_errors:
        st.error("Algumas linhas não puderam ser salvas.")
        for message in save_errors:
            st.markdown(
                f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:0.78rem;'
                f'color:{ERROR};margin:0.2rem 0;">— {message}</p>',
                unsafe_allow_html=True,
            )


# ── Build payloads (business logic — unchanged) ────────────────────────────────
def build_trade_create_payloads(
    *,
    edited_dataframe: pd.DataFrame,
    review_payload: PDFImportReviewPayload,
) -> tuple[list[dict[str, Any]], list[str]]:
    payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    default_trade_date = review_payload.normalized_trade_date.isoformat() if review_payload.normalized_trade_date else None
    default_broker     = review_payload.normalized_broker
    import_batch_id    = review_payload.import_job.batch_id if review_payload.import_job else None

    if import_batch_id is None:
        return [], ["O review não retornou um import_batch_id válido. Reenvie o PDF."]

    for row_number, record in enumerate(edited_dataframe.to_dict(orient="records"), start=1):
        if not bool(record.get("selected")):
            continue

        try:
            asset_ticker        = _clean_string(record.get("asset_ticker"))
            asset_classification = _clean_string(record.get("asset_classification"))
            operation_type      = _clean_string(record.get("operation_type"))
            trade_date          = _clean_string(record.get("trade_date")) or default_trade_date
            broker              = _clean_string(record.get("broker")) or default_broker
            quantity            = _coerce_int(record.get("quantity"))
            entry_price         = _coerce_decimal_string(record.get("entry_price"))
            exit_price          = _coerce_decimal_string(record.get("exit_price"),     allow_blank=True)
            gross_result        = _coerce_decimal_string(record.get("gross_result"),   allow_blank=True)
            fees                = _coerce_decimal_string(record.get("fees"),           allow_blank=True) or "0.00"
            net_result          = _coerce_decimal_string(record.get("net_result"),     allow_blank=True)
            confidence_score    = _coerce_float(record.get("confidence_score"),       allow_blank=True)
            source_page         = _coerce_int(record.get("source_page"),              allow_blank=True)
            notes               = _clean_string(record.get("notes"))

            if asset_classification not in {PDFAssetClassification.WIN.value, PDFAssetClassification.WDO.value}:
                raise ValueError("Apenas trades WIN e WDO podem ser salvos.")
            if not trade_date:
                raise ValueError("Data do trade obrigatória.")
            if not broker:
                raise ValueError("Corretora obrigatória.")
            if not asset_ticker:
                raise ValueError("Ticker obrigatório.")
            if operation_type not in {"buy", "sell"}:
                raise ValueError("Operation type deve ser buy ou sell.")
            if quantity is None or quantity <= 0:
                raise ValueError("Quantidade deve ser maior que zero.")
            if entry_price is None:
                raise ValueError("Preço de entrada obrigatório.")

            trade_time_raw = _clean_string(record.get("trade_time"))
            contract_code  = _clean_string(record.get("asset_ticker")) or None

            payloads.append(
                {
                    "trade_date":        trade_date,
                    "asset":             "WIN" if asset_classification == PDFAssetClassification.WIN.value else "WDO",
                    "asset_class":       "mini_index" if asset_classification == PDFAssetClassification.WIN.value else "mini_dollar",
                    "operation_type":    operation_type,
                    "status":            "closed" if exit_price else "draft",
                    "quantity":          quantity,
                    "entry_price":       entry_price,
                    "exit_price":        exit_price,
                    "gross_result":      gross_result,
                    "fees":              fees,
                    "net_result":        net_result,
                    "broker":            broker,
                    "setup_id":          None,
                    "source_type":       "pdf_import",
                    "imported_file_name": review_payload.filename,
                    "import_batch_id":   import_batch_id,
                    "trade_time":        trade_time_raw,
                    "contract_code":     contract_code,
                    "notes":             _merge_notes(notes=notes, source_page=source_page),
                    "confidence_score":  confidence_score,
                }
            )
        except ValueError as exc:
            errors.append(f"Linha {row_number}: {exc}")

    return payloads, errors


# ── Private helpers ────────────────────────────────────────────────────────────
def _summary_card(col, label: str, value: str, *, value_color: str = ON_SURFACE) -> None:
    with col:
        st.markdown(
            f"""
            <div style="background:{SURFACE_LOW};border:1px solid {OUTLINE};
                        border-radius:2px;padding:1rem 1.1rem;">
                <p style="font-family:'Space Grotesk',sans-serif;font-size:0.58rem;
                          font-weight:600;text-transform:uppercase;letter-spacing:0.09em;
                          color:{ON_SURFACE_VAR};margin:0 0 0.4rem 0;">{label}</p>
                <p style="font-family:'Space Grotesk',sans-serif;font-size:1.3rem;
                          font-weight:700;color:{value_color};margin:0;line-height:1.1;">{value}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _decimal_to_string(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value, "f")


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _coerce_decimal_string(value: Any, *, allow_blank: bool = False) -> str | None:
    cleaned = _clean_string(value)
    if cleaned is None:
        return None if allow_blank else None
    normalized = cleaned.replace("R$", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        decimal_value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Valor decimal inválido: {cleaned}") from exc
    return format(decimal_value, "f")


def _coerce_int(value: Any, *, allow_blank: bool = False) -> int | None:
    if value in {None, ""}:
        return None if allow_blank else None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Inteiro inválido: {value}") from exc


def _coerce_float(value: Any, *, allow_blank: bool = False) -> float | None:
    if value in {None, ""}:
        return None if allow_blank else None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Número inválido: {value}") from exc


def _merge_notes(*, notes: str | None, source_page: int | None) -> str | None:
    parts = [notes] if notes else []
    if source_page:
        parts.append(f"source_page={source_page}")
    return " | ".join(parts) if parts else None
