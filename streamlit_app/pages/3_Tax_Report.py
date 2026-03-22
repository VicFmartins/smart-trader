from __future__ import annotations

import sys
from pathlib import Path

# ── Path bootstrap ──────────────────────────────────────────────────────────
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if not sys.path or sys.path[0] != _project_root:
    sys.path.insert(0, _project_root)
del _project_root
# ───────────────────────────────────────────────────────────────────────────

import os
from decimal import Decimal

import pandas as pd
import streamlit as st

from streamlit_app.api_client import AuthSession, SmartTradeAPIClient, SmartTradeAPIError
from streamlit_app.style import (
    apply_theme, page_header, section_header, sidebar_brand, sidebar_section,
    kpi_card,
    BG, SURFACE_LOW, SURFACE, SURFACE_HIGH, SURFACE_HIGHEST,
    PRIMARY, TERTIARY, ERROR,
    ON_SURFACE, ON_SURFACE_VAR, OUTLINE,
)


DEFAULT_API_URL = os.environ.get("SMART_TRADE_API_URL", "http://127.0.0.1:8010")

st.set_page_config(page_title="Tax Report · Smart Trade", page_icon="ST", layout="wide")
apply_theme()
sidebar_brand("Tax Report")
page_header("Tax Report", "DARF 6015 · Day Trade B3 · Compensação automática de perdas")


def _format_brl(value) -> str:
    try:
        v = float(value)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "-"


def _darf_color(value) -> str:
    """Return TERTIARY for zero DARF, ERROR if positive (tax due)."""
    try:
        return ERROR if float(value) > 0 else ON_SURFACE_VAR
    except (TypeError, ValueError):
        return ON_SURFACE_VAR


def _pnl_color(value) -> str:
    try:
        return TERTIARY if float(value) >= 0 else ERROR
    except (TypeError, ValueError):
        return ON_SURFACE_VAR


def main() -> None:
    sidebar_section("Conexão")
    api_url = st.sidebar.text_input("FastAPI URL", value=st.session_state.get("smart_trade_api_url", DEFAULT_API_URL))
    st.session_state["smart_trade_api_url"] = api_url

    with st.sidebar.form("tax_login_form", clear_on_submit=False):
        email = st.text_input("Email", value=st.session_state.get("smart_trade_email", ""), key="tax_email")
        password = st.text_input("Senha", type="password", key="tax_password")
        login_submitted = st.form_submit_button("Entrar", use_container_width=True)

    if login_submitted:
        client = SmartTradeAPIClient(base_url=api_url)
        try:
            auth_session = client.login(email=email, password=password)
        except SmartTradeAPIError as exc:
            st.sidebar.error(exc.message)
        else:
            st.session_state["smart_trade_auth"] = auth_session
            st.session_state["smart_trade_email"] = email
            st.sidebar.success(f"✓ {auth_session.user_email}")

    auth_session: AuthSession | None = st.session_state.get("smart_trade_auth")
    if auth_session is None:
        st.info("Faça login para carregar o relatório de imposto.")
        return

    st.sidebar.success(f"✓ {auth_session.user_email}")

    if st.button("Atualizar relatório", type="primary"):
        _load_report(api_url=api_url, auth_session=auth_session)

    report = st.session_state.get("tax_report")
    if report is None:
        _load_report(api_url=api_url, auth_session=auth_session, show_spinner=False)
        report = st.session_state.get("tax_report")

    if report is None:
        return

    months = report.get("months", [])
    if not months:
        st.info("Nenhum trade fechado encontrado. Importe trades para ver o relatório de imposto.")
        return

    tax_rate_pct = float(report.get("tax_rate", 0.20)) * 100
    darf_code = months[0].get("darf_code", "6015")

    # ── Summary KPI row ──────────────────────────────────────────────────────
    last = months[-1]
    total_tax = sum(float(m.get("estimated_tax", 0)) for m in months)
    last_carryforward = float(last.get("remaining_loss_carryforward", 0))
    period_label = f"{report.get('generated_from', '-')} → {report.get('generated_to', '-')}"

    cols = st.columns(4, gap="small")
    with cols[0]:
        kpi_card("Período", period_label)
    with cols[1]:
        kpi_card("Meses calculados", str(len(months)))
    with cols[2]:
        kpi_card(
            f"DARF total estimado · {darf_code}",
            _format_brl(total_tax),
            value_color=ERROR if total_tax > 0 else ON_SURFACE_VAR,
        )
    with cols[3]:
        kpi_card(
            "Prejuízo acumulado atual",
            _format_brl(last_carryforward),
            value_color=ERROR if last_carryforward > 0 else ON_SURFACE_VAR,
        )

    # ── Metadata strip ───────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:0.68rem;'
        f'color:{ON_SURFACE_VAR};margin:0.9rem 0 1.5rem 0;letter-spacing:0.03em;">'
        f'Alíquota aplicada: <strong style="color:{ON_SURFACE};">{tax_rate_pct:.0f}%</strong>'
        f' &nbsp;·&nbsp; DARF código <strong style="color:{ON_SURFACE};">{darf_code}</strong>'
        f'</p>',
        unsafe_allow_html=True,
    )

    # ── Monthly breakdown table ──────────────────────────────────────────────
    section_header("Breakdown Mensal")
    _render_tax_table(months)

    # ── Disclaimer ───────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-top:1.5rem;padding:0.85rem 1.1rem;
                    background:{SURFACE_LOW};border-left:3px solid rgba(180,198,244,0.30);
                    border-radius:2px;">
            <p style="font-family:'Inter',sans-serif;font-size:0.78rem;
                      color:{ON_SURFACE_VAR};margin:0;line-height:1.6;">
                Os valores acima são <strong style="color:{ON_SURFACE};">estimativas</strong>
                baseadas nos trades salvos no journal.
                Consulte um contador para declaração oficial do IR.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_tax_table(months: list[dict]) -> None:
    """Render the monthly tax breakdown as a styled HTML table."""
    col_defs = [
        ("Mês",             "month",                    "left",  ON_SURFACE),
        ("Lucro bruto",     "gross_profit",             "right", None),
        ("Prejuízo bruto",  "gross_loss",               "right", None),
        ("Resultado líq.",  "net_result",               "right", None),
        ("Prej. anterior",  "prior_loss_carryforward",  "right", ON_SURFACE_VAR),
        ("Compensado",      "used_loss_offset",         "right", ON_SURFACE_VAR),
        ("Base de cálculo", "taxable_profit",           "right", None),
        ("DARF estimado",   "estimated_tax",            "right", "darf"),
        ("Prej. restante",  "remaining_loss_carryforward", "right", ON_SURFACE_VAR),
    ]

    header_cells = "".join(
        f'<th style="font-family:\'Space Grotesk\',sans-serif;font-size:0.60rem;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.07em;'
        f'color:{ON_SURFACE_VAR};padding:0.6rem 0.85rem;text-align:{align};">{label}</th>'
        for label, _, align, _ in col_defs
    )

    body_rows = ""
    for i, m in enumerate(months):
        row_bg = SURFACE if i % 2 == 0 else SURFACE_LOW
        cells = ""
        for label, key, align, color_hint in col_defs:
            raw = m.get(key, 0)
            if key == "month":
                display = str(raw) if raw else "-"
                color = ON_SURFACE
            elif color_hint == "darf":
                display = _format_brl(raw)
                color = _darf_color(raw)
            elif color_hint is None:
                # PnL-aware coloring
                display = _format_brl(raw)
                try:
                    fv = float(raw or 0)
                    color = TERTIARY if fv >= 0 else ERROR
                except (TypeError, ValueError):
                    color = ON_SURFACE_VAR
            else:
                display = _format_brl(raw)
                color = color_hint

            cells += (
                f'<td style="font-family:\'Space Grotesk\',sans-serif;font-size:0.78rem;'
                f'font-weight:500;color:{color};padding:0.65rem 0.85rem;'
                f'text-align:{align};white-space:nowrap;">{display}</td>'
            )

        body_rows += (
            f'<tr style="background:{row_bg};'
            f'border-bottom:1px solid {OUTLINE};">{cells}</tr>'
        )

    table_html = f"""
    <div style="overflow-x:auto;border:1px solid {OUTLINE};border-radius:2px;margin-top:0.5rem;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:{SURFACE_HIGHEST};border-bottom:1px solid {OUTLINE};">
                    {header_cells}
                </tr>
            </thead>
            <tbody>
                {body_rows}
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def _load_report(*, api_url: str, auth_session: AuthSession, show_spinner: bool = True) -> None:
    client = SmartTradeAPIClient(base_url=api_url)
    ctx = st.spinner("Calculando imposto...") if show_spinner else _noop_context()
    with ctx:
        try:
            report = client.get_tax_report(access_token=auth_session.access_token)
            st.session_state["tax_report"] = report
        except SmartTradeAPIError as exc:
            st.error(exc.message)


class _noop_context:
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass


main()
