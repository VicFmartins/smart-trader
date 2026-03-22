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

import streamlit as st

from streamlit_app.api_client import AuthSession, SmartTradeAPIClient, SmartTradeAPIError
from streamlit_app.style import apply_theme, page_header, sidebar_brand, sidebar_section
from streamlit_app.components.trade_dashboard import (
    apply_dashboard_style,
    build_filter_params,
    render_breakdown_charts,
    render_drawdown_curve,
    render_empty_dashboard,
    render_equity_curve,
    render_kpis,
    render_recent_trades_table,
)


DEFAULT_API_URL = os.environ.get("SMART_TRADE_API_URL", "http://127.0.0.1:8010")


st.set_page_config(page_title="Dashboard · Smart Trade", page_icon="ST", layout="wide")
apply_theme()
sidebar_brand("Trade Dashboard")
page_header("Trade Dashboard", "Performance · Equity · Drawdown · Breakdowns")


def main() -> None:
    apply_dashboard_style()
    sidebar_section("Conexão")
    api_url = st.sidebar.text_input("FastAPI URL", value=st.session_state.get("smart_trade_api_url", DEFAULT_API_URL))
    st.session_state["smart_trade_api_url"] = api_url

    with st.sidebar.form("dashboard_login_form", clear_on_submit=False):
        email = st.text_input("Email", value=st.session_state.get("smart_trade_email", ""), key="dashboard_email")
        password = st.text_input("Senha", type="password", key="dashboard_password")
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

    auth_session = st.session_state.get("smart_trade_auth")
    if auth_session is None:
        st.info("Faça login para carregar os analytics do journal.")
        return

    st.sidebar.success(f"✓ {auth_session.user_email}")
    sidebar_section("Filtros")
    date_range = st.sidebar.date_input("Periodo", value=(), help="Opcional. Se vazio, usa todo o historico.")
    asset = st.sidebar.selectbox("Ativo", options=["ALL", "WIN", "WDO"], index=0)
    setup_value = st.sidebar.text_input("Setup ID", value="")
    broker = st.sidebar.text_input("Broker", value="")

    if isinstance(date_range, tuple):
        date_from = date_range[0] if len(date_range) >= 1 else None
        date_to = date_range[1] if len(date_range) >= 2 else None
    else:
        date_from = date_range
        date_to = None

    filter_params = build_filter_params(
        date_from=date_from,
        date_to=date_to,
        asset=asset,
        setup_value=setup_value,
        broker=broker,
    )

    if st.button("Atualizar dashboard", type="primary"):
        _refresh_dashboard(api_url=api_url, auth_session=auth_session, filter_params=filter_params)

    snapshot = st.session_state.get("trade_dashboard_snapshot")
    recent_trades_payload = st.session_state.get("trade_dashboard_recent_trades")
    if snapshot is None or recent_trades_payload is None:
        _refresh_dashboard(api_url=api_url, auth_session=auth_session, filter_params=filter_params, rerun=False)
        snapshot = st.session_state.get("trade_dashboard_snapshot")
        recent_trades_payload = st.session_state.get("trade_dashboard_recent_trades")

    if snapshot is None:
        return
    if snapshot.summary.total_trades == 0:
        render_empty_dashboard()
        return

    render_kpis(snapshot)
    row_one = st.columns(2)
    with row_one[0]:
        render_equity_curve(snapshot)
    with row_one[1]:
        render_drawdown_curve(snapshot)

    render_breakdown_charts(snapshot)
    render_recent_trades_table(recent_trades_payload)


def _refresh_dashboard(
    *,
    api_url: str,
    auth_session: AuthSession,
    filter_params: dict,
    rerun: bool = False,
) -> None:
    client = SmartTradeAPIClient(base_url=api_url)
    recent_trades_params = {
        **filter_params,
        "limit": 15,
        "offset": 0,
        "sort_by": "trade_date",
        "sort_direction": "desc",
    }

    with st.spinner("Carregando dashboard..."):
        try:
            snapshot = client.get_trade_analytics(access_token=auth_session.access_token, params=filter_params)
            recent_trades = client.list_trades(access_token=auth_session.access_token, params=recent_trades_params)
        except SmartTradeAPIError as exc:
            st.error(exc.message)
            return

    st.session_state["trade_dashboard_snapshot"] = snapshot
    st.session_state["trade_dashboard_recent_trades"] = recent_trades
    if rerun:
        st.rerun()


main()
