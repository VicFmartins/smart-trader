from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.schemas.trade_analytics import TradeAnalyticsSnapshot
from streamlit_app.style import (
    BG, SURFACE_LOW, SURFACE, SURFACE_HIGH,
    PRIMARY, PRIMARY_CONT, TERTIARY, ERROR,
    ON_SURFACE, ON_SURFACE_VAR, OUTLINE,
    apply_theme, section_header,
)

# ── Plotly dark layout (matches the design system) ────────────────────────────
def _plotly_layout(**overrides) -> dict:
    base = dict(
        plot_bgcolor=SURFACE_LOW,
        paper_bgcolor=SURFACE,
        font=dict(
            family="Space Grotesk, Inter, sans-serif",
            color=ON_SURFACE_VAR,
            size=11,
        ),
        xaxis=dict(
            gridcolor=f"rgba(68,70,78,0.12)",
            showgrid=True,
            zeroline=False,
            linecolor=f"rgba(68,70,78,0.25)",
            tickfont=dict(family="Space Grotesk, sans-serif", color=ON_SURFACE_VAR, size=10),
        ),
        yaxis=dict(
            gridcolor=f"rgba(68,70,78,0.12)",
            showgrid=True,
            zeroline=False,
            linecolor=f"rgba(68,70,78,0.25)",
            tickfont=dict(family="Space Grotesk, sans-serif", color=ON_SURFACE_VAR, size=10),
        ),
        margin=dict(l=0, r=0, t=36, b=0),
        hoverlabel=dict(
            bgcolor=SURFACE_HIGH,
            bordercolor=f"rgba(68,70,78,0.35)",
            font=dict(family="Space Grotesk, sans-serif", color=ON_SURFACE, size=11),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=ON_SURFACE_VAR, size=10),
        ),
    )
    base.update(overrides)
    return base


def _chart_title(text: str) -> dict:
    return dict(
        text=text,
        font=dict(family="Manrope, sans-serif", size=13, color=ON_SURFACE),
        x=0,
        xanchor="left",
        pad=dict(l=0, b=8),
    )


# ── Public API ─────────────────────────────────────────────────────────────────
def apply_dashboard_style() -> None:
    """Inject global theme (called by the dashboard page)."""
    apply_theme()


def render_empty_dashboard() -> None:
    st.markdown(
        f"""
        <div style="background:{SURFACE_LOW};border:1px solid {OUTLINE};border-radius:2px;
                    padding:3rem 2rem;text-align:center;margin-top:1rem;">
            <p style="font-family:'Space Grotesk',sans-serif;font-size:0.65rem;font-weight:600;
                      text-transform:uppercase;letter-spacing:0.10em;color:{ON_SURFACE_VAR};
                      margin:0 0 0.6rem 0;">Sem dados</p>
            <p style="font-family:'Inter',sans-serif;font-size:0.9rem;color:{ON_SURFACE_VAR};
                      margin:0;">Nenhum trade encontrado para os filtros selecionados.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(snapshot: TradeAnalyticsSnapshot) -> None:
    max_drawdown = min((p.drawdown for p in snapshot.drawdown_curve), default=0.0)
    net_pnl      = float(snapshot.summary.net_pnl)
    win_rate     = float(snapshot.summary.win_rate)
    pf           = snapshot.summary.profit_factor
    expectancy   = float(snapshot.summary.expectancy) if snapshot.summary.expectancy is not None else None

    pnl_color    = TERTIARY if net_pnl >= 0 else ERROR
    wr_color     = TERTIARY if win_rate >= 50 else ERROR
    pf_color     = TERTIARY if (pf or 0) >= 1 else ERROR

    cols = st.columns(5, gap="small")

    _kpi(cols[0], "Net P&L",        _fmt_brl(net_pnl),       value_color=pnl_color)
    _kpi(cols[1], "Win Rate",       f"{win_rate:.1f}%",      value_color=wr_color)
    _kpi(cols[2], "Profit Factor",  "-" if pf is None else f"{pf:.2f}", value_color=pf_color)
    _kpi(cols[3], "Expectancy",     _fmt_brl(expectancy) if expectancy is not None else "-")
    _kpi(cols[4], "Max Drawdown",   _fmt_brl(max_drawdown),  value_color=ERROR,
         sub_label=f"{snapshot.summary.total_trades} trades")


def render_equity_curve(snapshot: TradeAnalyticsSnapshot) -> None:
    section_header("Equity Curve")
    if not snapshot.equity_curve:
        _empty_chart("Sem dados para a curva de equity.")
        return

    df = pd.DataFrame([p.model_dump() for p in snapshot.equity_curve])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["trade_date"],
        y=df["equity"],
        mode="lines",
        line=dict(color=TERTIARY, width=2),
        fill="tozeroy",
        fillcolor="rgba(47,217,244,0.06)",
        name="Equity",
        hovertemplate="<b>%{x}</b><br>Equity: R$ %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        **_plotly_layout(title=_chart_title("Equity Curve")),
        yaxis_tickprefix="R$ ",
        yaxis_tickformat=",.0f",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_drawdown_curve(snapshot: TradeAnalyticsSnapshot) -> None:
    section_header("Drawdown")
    if not snapshot.drawdown_curve:
        _empty_chart("Sem dados para o drawdown.")
        return

    df = pd.DataFrame([p.model_dump() for p in snapshot.drawdown_curve])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["trade_date"],
        y=df["drawdown"],
        fill="tozeroy",
        mode="lines",
        line=dict(color=ERROR, width=1.5),
        fillcolor="rgba(255,180,171,0.08)",
        name="Drawdown",
        hovertemplate="<b>%{x}</b><br>Drawdown: R$ %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        **_plotly_layout(title=_chart_title("Drawdown")),
        yaxis_tickprefix="R$ ",
        yaxis_tickformat=",.0f",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_breakdown_charts(snapshot: TradeAnalyticsSnapshot) -> None:
    row_a = st.columns(2, gap="medium")
    row_b = st.columns(2, gap="medium")

    with row_a[0]:
        _bar_chart("PnL por Ativo",         snapshot.pnl_by_asset,    x="label", y="pnl")
    with row_a[1]:
        _bar_chart("PnL por Setup",         snapshot.pnl_by_setup,    x="label", y="pnl")
    with row_b[0]:
        _bar_chart("PnL por Dia da Semana", snapshot.pnl_by_weekday,  x="label", y="pnl")
    with row_b[1]:
        _bar_chart("PnL por Hora",          snapshot.pnl_by_hour,     x="hour",  y="pnl")


def render_recent_trades_table(recent_trades_payload: dict[str, Any]) -> None:
    section_header("Trades Recentes")
    rows = recent_trades_payload.get("data", [])
    if not rows:
        _empty_chart("Nenhum trade recente para mostrar.")
        return

    df = pd.DataFrame(rows)
    visible = [
        "trade_date", "asset", "operation_type", "quantity",
        "entry_price", "exit_price", "net_result",
        "broker", "source_type", "created_at",
    ]
    visible = [c for c in visible if c in df.columns]

    # Rename for display
    rename_map = {
        "trade_date": "Data", "asset": "Ativo", "operation_type": "Lado",
        "quantity": "Qtd", "entry_price": "Entrada", "exit_price": "Saída",
        "net_result": "Líquido", "broker": "Corretora",
        "source_type": "Origem", "created_at": "Criado em",
    }
    display_df = df[visible].rename(columns=rename_map)
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def build_filter_params(
    *,
    date_from,
    date_to,
    asset: str,
    setup_value: str,
    broker: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if date_from is not None:
        params["date_from"] = date_from.isoformat()
    if date_to is not None:
        params["date_to"] = date_to.isoformat()
    if asset and asset != "ALL":
        params["asset"] = asset
    if broker.strip():
        params["broker"] = broker.strip()
    if setup_value.strip():
        params["setup_id"] = int(setup_value.strip())
    return params


# ── Private helpers ────────────────────────────────────────────────────────────
def _kpi(col, label: str, value: str, *, value_color: str = ON_SURFACE, sub_label: str = "") -> None:
    sub_html = (
        f'<p style="font-family:\'Space Grotesk\',sans-serif;font-size:0.65rem;'
        f'color:{ON_SURFACE_VAR};margin:0.3rem 0 0 0;">{sub_label}</p>'
        if sub_label else ""
    )
    with col:
        st.markdown(
            f"""
            <div style="background:{SURFACE_LOW};border:1px solid {OUTLINE};
                        border-radius:2px;padding:1.1rem 1.25rem;">
                <p style="font-family:'Space Grotesk',sans-serif;font-size:0.60rem;
                          font-weight:600;text-transform:uppercase;letter-spacing:0.09em;
                          color:{ON_SURFACE_VAR};margin:0 0 0.45rem 0;">{label}</p>
                <p style="font-family:'Space Grotesk',sans-serif;font-size:1.35rem;
                          font-weight:700;color:{value_color};margin:0;line-height:1.1;">{value}</p>
                {sub_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def _bar_chart(title: str, items: list[Any], *, x: str, y: str) -> None:
    section_header(title)
    if not items:
        _empty_chart("Sem dados.")
        return

    df = pd.DataFrame([item.model_dump() for item in items])
    if df.empty or df[y].fillna(0).abs().sum() == 0:
        _empty_chart("Sem dados relevantes.")
        return

    colors = [TERTIARY if v >= 0 else ERROR for v in df[y]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x],
        y=df[y],
        marker_color=colors,
        hovertemplate="%{x}: R$ %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        **_plotly_layout(),
        yaxis_tickprefix="R$ ",
        yaxis_tickformat=",.0f",
        showlegend=False,
        bargap=0.35,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _empty_chart(msg: str) -> None:
    st.markdown(
        f"""
        <div style="background:{SURFACE_LOW};border:1px solid {OUTLINE};border-radius:2px;
                    padding:1.5rem;text-align:center;">
            <p style="font-family:'Inter',sans-serif;font-size:0.82rem;
                      color:{ON_SURFACE_VAR};margin:0;">{msg}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_brl(value: float | int | None) -> str:
    if value is None:
        return "-"
    sign = "+" if float(value) > 0 else ""
    return f"{sign}R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
