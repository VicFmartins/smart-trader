from __future__ import annotations

# ── Path bootstrap ─────────────────────────────────────────────────────────────
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if not sys.path or sys.path[0] != _project_root:
    sys.path.insert(0, _project_root)
del _project_root
# ──────────────────────────────────────────────────────────────────────────────

import streamlit as st

from streamlit_app.style import (
    PRIMARY, SURFACE_LOW, ON_SURFACE, ON_SURFACE_VAR, OUTLINE, TERTIARY,
    apply_theme,
)

st.set_page_config(
    page_title="Smart Trade",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

# ── Sidebar brand ──────────────────────────────────────────────────────────────
st.sidebar.markdown(
    f"""
    <div style="padding:0 1rem 1.5rem 1rem;border-bottom:1px solid {OUTLINE};
                margin-bottom:0.75rem;">
        <h1 style="font-family:'Manrope',sans-serif;font-size:1.2rem;font-weight:800;
                   color:{PRIMARY};letter-spacing:-0.02em;margin:0;">Smart Trade</h1>
        <p style="font-family:'Space Grotesk',sans-serif;font-size:0.58rem;
                  text-transform:uppercase;letter-spacing:0.12em;
                  color:{ON_SURFACE_VAR};margin:0.2rem 0 0 0;opacity:0.6;">
            Institutional Grade
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Hero section ───────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="max-width:680px;padding:3rem 0 2.5rem 0;">
        <p style="font-family:'Space Grotesk',sans-serif;font-size:0.65rem;font-weight:600;
                  text-transform:uppercase;letter-spacing:0.14em;color:{PRIMARY};
                  margin:0 0 0.75rem 0;opacity:0.8;">
            Day Trade Journal · Local-First
        </p>
        <h1 style="font-family:'Manrope',sans-serif;font-size:2.4rem;font-weight:800;
                   color:{ON_SURFACE};letter-spacing:-0.04em;line-height:1.15;margin:0 0 1rem 0;">
            Smart Trade
        </h1>
        <p style="font-family:'Inter',sans-serif;font-size:0.95rem;color:{ON_SURFACE_VAR};
                  line-height:1.65;margin:0 0 2rem 0;max-width:520px;">
            Workspace para análise e importação de notas de corretagem
            com extração inteligente via IA, analytics de performance
            e cálculo automático de DARF.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Feature cards ──────────────────────────────────────────────────────────────
cols = st.columns(3, gap="medium")

_features = [
    (
        "📄",
        "PDF Import",
        "Faça upload de notas de corretagem. Gemini extrai os trades automaticamente "
        "e apresenta um preview editável antes de salvar.",
        "1_PDF_Import_Review",
    ),
    (
        "📊",
        "Trade Dashboard",
        "Equity curve, drawdown, win rate, profit factor e breakdowns por ativo, "
        "horário e dia da semana.",
        "2_Trade_Dashboard",
    ),
    (
        "🧾",
        "Tax Report",
        "Cálculo mensal de DARF 6015 com compensação automática de perdas "
        "acumuladas e alíquota de 20%.",
        "3_Tax_Report",
    ),
]

for col, (icon, title, desc, _page) in zip(cols, _features):
    with col:
        st.markdown(
            f"""
            <div style="background:{SURFACE_LOW};border:1px solid {OUTLINE};
                        border-radius:2px;padding:1.5rem 1.5rem 1.75rem 1.5rem;
                        height:100%;">
                <p style="font-size:1.6rem;margin:0 0 0.75rem 0;">{icon}</p>
                <p style="font-family:'Manrope',sans-serif;font-size:0.95rem;
                          font-weight:700;color:{ON_SURFACE};
                          margin:0 0 0.6rem 0;">{title}</p>
                <p style="font-family:'Inter',sans-serif;font-size:0.82rem;
                          color:{ON_SURFACE_VAR};line-height:1.6;margin:0;">{desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Status strip ───────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-top:2.5rem;padding:0.9rem 1.25rem;
                background:{SURFACE_LOW};border:1px solid {OUTLINE};border-radius:2px;
                display:flex;align-items:center;gap:0.6rem;">
        <span style="width:7px;height:7px;border-radius:50%;
                     background:{TERTIARY};display:inline-block;
                     box-shadow:0 0 6px {TERTIARY};flex-shrink:0;"></span>
        <p style="font-family:'Space Grotesk',sans-serif;font-size:0.72rem;
                  color:{ON_SURFACE_VAR};margin:0;letter-spacing:0.02em;">
            Backend local · Use a barra lateral para navegar entre as páginas
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
