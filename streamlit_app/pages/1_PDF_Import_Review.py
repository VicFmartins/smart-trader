from __future__ import annotations

import sys
from pathlib import Path

# ── Path bootstrap ──────────────────────────────────────────────────────────
# Streamlit's modified_sys_path re-inserts streamlit_app/ at sys.path[0]
# before every page execution, which shadows the backend `app/` package with
# streamlit_app/app.py.  Re-inserting the project root at position 0 here —
# inside the page script, after Streamlit's insertion — gives the real `app/`
# package priority for this and all subsequent imports in this run.
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if not sys.path or sys.path[0] != _project_root:
    sys.path.insert(0, _project_root)
del _project_root
# ───────────────────────────────────────────────────────────────────────────

import os
from io import BytesIO

import streamlit as st

from app.schemas.pdf_import import PDFImportReviewPayload
from streamlit_app.api_client import AuthSession, SmartTradeAPIClient, SmartTradeAPIError
from streamlit_app.components.pdf_review import (
    build_trade_create_payloads,
    render_editable_trade_table,
    render_global_warnings,
    render_review_summary,
    render_save_results,
    review_payload_to_dataframe,
)


from streamlit_app.style import (
    apply_theme, page_header, section_header, sidebar_brand, sidebar_section,
    ON_SURFACE_VAR,
)


DEFAULT_API_URL = os.environ.get("SMART_TRADE_API_URL", "http://127.0.0.1:8010")

st.set_page_config(page_title="PDF Import · Smart Trade", page_icon="ST", layout="wide")
apply_theme()
sidebar_brand("PDF Import")
page_header("PDF Import Review", "Notas de corretagem · Extração via IA")


def main() -> None:
    sidebar_section("Conexão")
    api_url = st.sidebar.text_input("FastAPI URL", value=st.session_state.get("smart_trade_api_url", DEFAULT_API_URL))
    st.session_state["smart_trade_api_url"] = api_url

    with st.sidebar.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", value=st.session_state.get("smart_trade_email", ""))
        password = st.text_input("Senha", type="password")
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
        st.info("Faça login no FastAPI local para habilitar o upload do PDF.")
        return

    st.sidebar.success(f"✓ {auth_session.user_email}")
    uploaded_file = st.file_uploader("Escolha a nota de corretagem em PDF", type=["pdf"])
    upload_clicked = st.button("Extrair trades do PDF", type="primary", disabled=uploaded_file is None)

    if upload_clicked and uploaded_file is not None:
        review_payload = _run_pdf_review(api_url=api_url, auth_session=auth_session, uploaded_file=uploaded_file)
        if review_payload is not None:
            st.session_state["pdf_review_payload"] = review_payload
            st.session_state["pdf_review_table"] = review_payload_to_dataframe(review_payload)

    review_payload: PDFImportReviewPayload | None = st.session_state.get("pdf_review_payload")
    if review_payload is None:
        return

    render_review_summary(review_payload)
    render_global_warnings(review_payload)
    section_header("Trades Extraídos")
    edited_dataframe = render_editable_trade_table(st.session_state["pdf_review_table"])
    st.session_state["pdf_review_table"] = edited_dataframe

    selected_rows = int(edited_dataframe["selected"].fillna(False).sum()) if not edited_dataframe.empty else 0
    st.markdown(
        f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:0.70rem;'
        f'color:{ON_SURFACE_VAR};margin:0.5rem 0 0.75rem 0;letter-spacing:0.03em;">'
        f'{selected_rows} linha(s) marcada(s) para salvar.</p>',
        unsafe_allow_html=True,
    )

    if st.button("Confirmar e salvar selecionadas", type="primary", disabled=selected_rows == 0):
        _save_selected_rows(
            api_url=api_url,
            auth_session=auth_session,
            review_payload=review_payload,
            edited_dataframe=edited_dataframe,
        )


def _run_pdf_review(
    *,
    api_url: str,
    auth_session: AuthSession,
    uploaded_file,
) -> PDFImportReviewPayload | None:
    client = SmartTradeAPIClient(base_url=api_url)
    file_bytes = BytesIO(uploaded_file.getvalue()).read()

    with st.spinner("Extraindo texto e revisando trades..."):
        try:
            return client.review_pdf_import(
                file_name=uploaded_file.name,
                file_bytes=file_bytes,
                access_token=auth_session.access_token,
            )
        except SmartTradeAPIError as exc:
            st.error(exc.message)
            return None


def _save_selected_rows(
    *,
    api_url: str,
    auth_session: AuthSession,
    review_payload: PDFImportReviewPayload,
    edited_dataframe,
) -> None:
    trade_payloads, local_errors = build_trade_create_payloads(
        edited_dataframe=edited_dataframe,
        review_payload=review_payload,
    )
    if not trade_payloads:
        st.error("Nenhuma linha valida foi preparada para salvar.")
        render_save_results([], local_errors)
        return

    client = SmartTradeAPIClient(base_url=api_url)
    save_errors = list(local_errors)

    saved_rows: list[dict] = []
    with st.spinner("Salvando trades selecionados..."):
        try:
            response = client.create_trades_bulk(
                trade_payloads=trade_payloads,
                access_token=auth_session.access_token,
            )
            saved_rows = response.get("trades", [])
        except SmartTradeAPIError as exc:
            save_errors.append(exc.message)

    render_save_results(saved_rows, save_errors)


main()
