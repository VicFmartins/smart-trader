"""
Smart Trade — global design system.

Call ``apply_theme()`` once at the top of every Streamlit page (after
``st.set_page_config``).  The CSS is idempotent; injecting it multiple
times is harmless.
"""
from __future__ import annotations

import streamlit as st


# ── Design tokens (mirrored from DESIGN.md / Stitch mockups) ─────────────────
BG              = "#0f131e"
SURFACE_LOW     = "#171b27"
SURFACE         = "#1b1f2b"
SURFACE_HIGH    = "#262a36"
SURFACE_HIGHEST = "#313441"
PRIMARY         = "#b4c6f4"
PRIMARY_CONT    = "#0a1f44"
TERTIARY        = "#2fd9f4"   # positive / profit
ERROR           = "#ffb4ab"   # negative / loss
ON_SURFACE      = "#dfe2f2"
ON_SURFACE_VAR  = "#c5c6cf"
OUTLINE         = "rgba(68,70,78,0.20)"
OUTLINE_HOVER   = "rgba(68,70,78,0.40)"
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ── CSS tokens ── */
:root {
    --bg:              #0f131e;
    --surface-low:     #171b27;
    --surface:         #1b1f2b;
    --surface-high:    #262a36;
    --surface-highest: #313441;
    --primary:         #b4c6f4;
    --primary-cont:    #0a1f44;
    --tertiary:        #2fd9f4;
    --error:           #ffb4ab;
    --on-surface:      #dfe2f2;
    --on-surface-var:  #c5c6cf;
    --outline:         rgba(68,70,78,0.20);
    --radius:          2px;
    --transition:      200ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── App base ── */
.stApp {
    background-color: var(--bg) !important;
    color: var(--on-surface);
    font-family: 'Inter', sans-serif;
}
.stApp > header { display: none !important; }
#MainMenu, footer { visibility: hidden; }

/* ── Remove default top padding from main block ── */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* ── Headings ── */
h1, h2, h3, h4 {
    font-family: 'Manrope', sans-serif !important;
    color: var(--on-surface) !important;
    letter-spacing: -0.02em;
}
h1 { font-size: 1.6rem  !important; font-weight: 800 !important; }
h2 { font-size: 1.15rem !important; font-weight: 700 !important; }
h3 { font-size: 1rem    !important; font-weight: 600 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--bg) !important;
    border-right: 1px solid var(--outline) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem !important;
}

/* ── Sidebar nav links (Streamlit multipage) ── */
a[data-testid="stSidebarNavLink"] {
    color: var(--on-surface-var) !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.65rem 1rem !important;
    border-radius: 0 !important;
    border-right: 2px solid transparent !important;
    transition: all var(--transition) !important;
    text-decoration: none !important;
}
a[data-testid="stSidebarNavLink"]:hover {
    background-color: var(--surface) !important;
    color: var(--on-surface) !important;
    border-right-color: transparent !important;
}
a[data-testid="stSidebarNavLink"][aria-selected="true"] {
    background-color: var(--primary-cont) !important;
    color: var(--primary) !important;
    border-right: 2px solid var(--primary) !important;
}
/* Page icon inside nav link */
a[data-testid="stSidebarNavLink"] svg,
a[data-testid="stSidebarNavLink"] img {
    opacity: 0.6;
}
a[data-testid="stSidebarNavLink"][aria-selected="true"] svg,
a[data-testid="stSidebarNavLink"][aria-selected="true"] img {
    opacity: 1;
}

/* ── Sidebar text inputs / labels ── */
[data-testid="stSidebar"] label {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--on-surface-var) !important;
}
[data-testid="stSidebar"] .stSubheader,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--on-surface-var) !important;
    margin-bottom: 0.5rem !important;
}

/* ── All text inputs & select boxes ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    background-color: var(--surface) !important;
    border: 1px solid var(--outline) !important;
    border-radius: var(--radius) !important;
    color: var(--on-surface) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.875rem !important;
    transition: border-color var(--transition) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: rgba(180,198,244,0.40) !important;
    background-color: var(--primary-cont) !important;
    box-shadow: 0 0 0 2px rgba(180,198,244,0.08) !important;
}
[data-testid="stSelectbox"] > div > div {
    background-color: var(--surface) !important;
    border: 1px solid var(--outline) !important;
    border-radius: var(--radius) !important;
    color: var(--on-surface) !important;
}

/* ── Password input ── */
[data-testid="stTextInput"][data-baseweb="input"] input[type="password"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── Buttons ── */
button[kind="primary"],
.stButton button[kind="primary"] {
    background-color: var(--primary-cont) !important;
    color: var(--primary) !important;
    border: 1px solid rgba(180,198,244,0.25) !important;
    border-radius: var(--radius) !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.05em !important;
    transition: all var(--transition) !important;
}
button[kind="primary"]:hover,
.stButton button[kind="primary"]:hover {
    border-color: var(--primary) !important;
    opacity: 0.9 !important;
}
button[kind="secondary"],
.stButton button[kind="secondary"] {
    background-color: transparent !important;
    color: var(--on-surface-var) !important;
    border: 1px solid var(--outline) !important;
    border-radius: var(--radius) !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    transition: all var(--transition) !important;
}
button[kind="secondary"]:hover {
    background-color: var(--surface) !important;
    color: var(--on-surface) !important;
    border-color: rgba(68,70,78,0.40) !important;
}

/* ── Form submit buttons ── */
[data-testid="stFormSubmitButton"] button {
    background-color: var(--primary-cont) !important;
    color: var(--primary) !important;
    border: 1px solid rgba(180,198,244,0.25) !important;
    border-radius: var(--radius) !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.04em !important;
    width: 100% !important;
    transition: all var(--transition) !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    border-color: var(--primary) !important;
    opacity: 0.9 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploaderDropzone"] {
    background-color: var(--surface-low) !important;
    border: 1px dashed rgba(180,198,244,0.20) !important;
    border-radius: var(--radius) !important;
    transition: all var(--transition) !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: rgba(180,198,244,0.50) !important;
    background-color: var(--primary-cont) !important;
}
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p {
    color: var(--on-surface-var) !important;
    font-family: 'Manrope', sans-serif !important;
}
[data-testid="stFileUploaderDropzone"] svg {
    color: var(--primary) !important;
    fill: var(--primary) !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background-color: var(--surface-low) !important;
    border: 1px solid var(--outline) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stExpander"] summary {
    color: var(--on-surface-var) !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
}
[data-testid="stExpander"] summary:hover {
    color: var(--on-surface) !important;
}

/* ── Metric cards (st.metric) ── */
[data-testid="stMetric"] {
    background-color: var(--surface-low) !important;
    border: 1px solid var(--outline) !important;
    border-radius: var(--radius) !important;
    padding: 1.1rem 1.25rem !important;
}
[data-testid="stMetric"] label {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.62rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    color: var(--on-surface-var) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: var(--on-surface) !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.7rem !important;
}

/* ── DataFrames / data editors ── */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    border: 1px solid var(--outline) !important;
    border-radius: var(--radius) !important;
    overflow: hidden;
}

/* ── Alert boxes ── */
[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
}
.stAlert[data-baseweb="notification"] {
    border-left-width: 3px !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] > div {
    border-top-color: var(--primary) !important;
}

/* ── Caption / small text ── */
[data-testid="stCaptionContainer"],
.stCaption {
    color: var(--on-surface-var) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.04em !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--outline) !important;
    margin: 1.5rem 0 !important;
}

/* ── Info / success / warning / error message boxes ── */
div[data-testid="stAlert"][role="alert"] {
    border-radius: var(--radius) !important;
}

/* ── Scrollbar (webkit) ── */
::-webkit-scrollbar            { width: 4px; height: 4px; }
::-webkit-scrollbar-track      { background: var(--bg); }
::-webkit-scrollbar-thumb      { background: var(--surface-highest); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(180,198,244,0.30); }

/* ── Selectbox popup ── */
[data-baseweb="popover"] ul {
    background-color: var(--surface) !important;
    border: 1px solid var(--outline) !important;
}
[data-baseweb="popover"] ul li:hover {
    background-color: var(--surface-high) !important;
}

/* ── Checkbox (in data_editor) ── */
[data-testid="stDataEditor"] input[type="checkbox"]:checked {
    accent-color: var(--primary) !important;
}

/* ── st.info / st.success coloring ── */
.element-container .stAlert > div {
    font-size: 0.85rem !important;
}

</style>
"""


def apply_theme() -> None:
    """Inject the Smart Trade design system CSS into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    """Render a consistent premium page header (replaces st.title / st.caption)."""
    sub_html = (
        f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:0.68rem;'
        f'text-transform:uppercase;letter-spacing:0.10em;color:{ON_SURFACE_VAR};'
        f'margin:0.25rem 0 0 0;opacity:0.75;">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div style="padding:0.25rem 0 1.75rem 0;border-bottom:1px solid {OUTLINE};margin-bottom:1.75rem;">
            <h1 style="font-family:'Manrope',sans-serif;font-size:1.55rem;font-weight:800;
                       color:{ON_SURFACE};letter-spacing:-0.03em;margin:0;">{title}</h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    """Render a consistent section subheading (replaces st.subheader)."""
    st.markdown(
        f"""
        <p style="font-family:'Manrope',sans-serif;font-size:0.65rem;font-weight:700;
                  text-transform:uppercase;letter-spacing:0.10em;color:{ON_SURFACE_VAR};
                  margin:1.5rem 0 0.75rem 0;">{title}</p>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(
    label: str,
    value: str,
    *,
    value_color: str = ON_SURFACE,
    sub_label: str = "",
) -> None:
    """Render a single premium KPI card via st.markdown inside the current column."""
    sub_html = (
        f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:0.65rem;'
        f'color:{ON_SURFACE_VAR};margin:0.35rem 0 0 0;">{sub_label}</p>'
        if sub_label else ""
    )
    st.markdown(
        f"""
        <div style="background:{SURFACE_LOW};border:1px solid {OUTLINE};
                    border-radius:2px;padding:1.25rem 1.4rem;height:100%;">
            <p style="font-family:'Space Grotesk',sans-serif;font-size:0.60rem;
                      font-weight:600;text-transform:uppercase;letter-spacing:0.09em;
                      color:{ON_SURFACE_VAR};margin:0 0 0.45rem 0;">{label}</p>
            <p style="font-family:'Space Grotesk',sans-serif;font-size:1.45rem;
                      font-weight:700;color:{value_color};margin:0;line-height:1.1;">{value}</p>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand(page_name: str = "") -> None:
    """Render the Smart Trade brand block at the top of the sidebar."""
    st.sidebar.markdown(
        f"""
        <div style="padding:0 1rem 1.5rem 1rem;border-bottom:1px solid {OUTLINE};margin-bottom:0.75rem;">
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


def sidebar_section(label: str) -> None:
    """Render a small uppercase section label in the sidebar."""
    st.sidebar.markdown(
        f"""
        <p style="font-family:'Space Grotesk',sans-serif;font-size:0.60rem;font-weight:600;
                  text-transform:uppercase;letter-spacing:0.10em;color:{ON_SURFACE_VAR};
                  margin:1.1rem 0 0.4rem 0;padding:0 1rem;">{label}</p>
        """,
        unsafe_allow_html=True,
    )
