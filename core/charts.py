"""Plotly charts matching the reference dashboard's Chart.js look."""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core import theme

TEAL_BAR = "#14b8a6"
ORIGIN_BAR = "rgba(45,212,191,.85)"
AMBER_LINE = "#f59e0b"
ROSE_BAR = "#f43f5e"
BLUE_BAR = "#3b82f6"
LABEL = "#e2e8f0"


def _empty(msg: str = "No data for the selected filters.") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        font=dict(family=theme.FONT, size=13, color=theme.MUTED),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return theme.style_fig(fig, height=265)


def _fmt(values) -> list[str]:
    out = []
    for v in values:
        if v is None or (isinstance(v, float) and math.isnan(v)) or v == 0:
            out.append("")
        else:
            out.append(f"{v:,.0f}")
    return out


def _nice_step(value: float) -> float:
    """1/2/2.5/5/10 x 10^n, so axis ticks look like Chart.js."""
    if value <= 0:
        return 1.0
    exp = math.floor(math.log10(value))
    base = 10 ** exp
    for mult in (1, 2, 2.5, 5, 10):
        if value <= mult * base:
            return mult * base
    return 10 * base


def location_stock(loc: pd.DataFrame) -> go.Figure:
    if loc.empty or loc["stock"].sum() <= 0:
        return _empty()
    d = loc.sort_values("stock", ascending=False)

    fig = go.Figure(go.Bar(
        x=list(d.index),
        y=d["stock"],
        marker=dict(color=TEAL_BAR, line=dict(width=0)),
        text=_fmt(d["stock"]),
        textposition="outside",
        textfont=dict(family=theme.FONT, size=10, color=LABEL),
        cliponaxis=False,
        width=0.62,
        hovertemplate="<b>%{x}</b><br>Stock: %{y:,.0f} MT<extra></extra>",
    ))
    theme.style_fig(fig, height=265)
    fig.update_layout(
        margin=dict(l=6, r=10, t=18, b=6),
        yaxis=dict(range=[0, float(d["stock"].max()) * 1.12], nticks=11),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(title="")
    return fig


def origin_combo(org: pd.DataFrame) -> go.Figure:
    if org.empty or org["stock"].sum() <= 0:
        return _empty()
    d = org.sort_values("avg_stock_per_entry", ascending=False)
    max_avg = float(d["avg_stock_per_entry"].max()) if len(d) else 0.0
    y_top = max(1000, math.ceil(max_avg * 1.5 / 1000) * 1000)
    rate_max = float(d["avg_rate"].max()) if len(d) else 0.0
    rate_step = _nice_step(rate_max / 5) if rate_max > 0 else 1000
    rate_top = rate_step * math.ceil(rate_max / rate_step) if rate_max > 0 else 1000

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=list(d.index),
            y=d["avg_stock_per_entry"],
            name="Avg stock (MT)",
            marker=dict(color=ORIGIN_BAR, line=dict(width=0)),
            text=_fmt(d["avg_stock_per_entry"]),
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(family=theme.FONT, size=10, color="#04211d"),
            width=0.5,
            hovertemplate="<b>%{x}</b><br>Avg stock / entry: %{y:,.0f} MT<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=list(d.index),
            y=d["avg_rate"],
            name="Avg sale rate (BDT/MT)",
            mode="lines+markers+text",
            line=dict(color=AMBER_LINE, width=3, shape="spline", smoothing=1.1),
            marker=dict(size=6, color=AMBER_LINE),
            text=[f"{v:,.0f}" if pd.notna(v) else "" for v in d["avg_rate"]],
            textposition="top center",
            textfont=dict(family=theme.FONT, size=10, color=theme.AMBER),
            hovertemplate="<b>%{x}</b><br>Avg sale rate: %{y:,.0f} BDT/MT<extra></extra>",
        ),
        secondary_y=True,
    )

    theme.style_fig(fig, height=265)
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="top", y=-0.24, xanchor="center", x=0.5,
            font=dict(size=11, color=theme.MUTED), bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
        ),
        margin=dict(l=8, r=8, t=18, b=44),
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(
        title_text="Avg stock (MT)", title_font=dict(size=11, color="#5eead4"),
        range=[0, y_top], secondary_y=False, gridcolor=theme.GRID,
    )
    fig.update_yaxes(
        title_text="Avg rate (BDT/MT)", title_font=dict(size=11, color=theme.AMBER),
        secondary_y=True, showgrid=False, rangemode="tozero",
        tickfont=dict(size=11, color=theme.AMBER),
        range=[0, rate_top], dtick=rate_step, tickformat=",.0f",
    )
    return fig


def _hbar(df: pd.DataFrame, value: str, color: str,
          tooltip: str) -> go.Figure:
    d = df[df[value].notna()].sort_values(value, ascending=False)
    if d.empty:
        return _empty()

    fig = go.Figure(go.Bar(
        x=d[value],
        y=list(d.index),
        orientation="h",
        marker=dict(color=color, line=dict(width=0)),
        text=[f"{v:,.0f}" for v in d[value]],
        textposition="outside",
        textfont=dict(family=theme.FONT, size=10, color=LABEL),
        cliponaxis=False,
        width=0.85,
        hovertemplate="<b>%{y}</b><br>" + tooltip + ": %{x:,.0f}<extra></extra>",
    ))
    theme.style_fig(fig, height=265)
    fig.update_layout(
        margin=dict(l=10, r=58, t=14, b=6),
        bargap=0.25,
        yaxis=dict(autorange="reversed"),
    )
    fig.update_xaxes(showgrid=True, title="", range=[0, float(d[value].max()) * 1.05])
    fig.update_yaxes(showgrid=False, title="", tickfont=dict(size=10.5))
    return fig


def importer_rates(imp: pd.DataFrame) -> go.Figure:
    d = imp[imp["avg_rate"].notna()].copy()
    return _hbar(d, "avg_rate", ROSE_BAR, "Avg sale rate (BDT/MT)")


def importer_stock(imp: pd.DataFrame) -> go.Figure:
    d = imp[imp["stock"] > 0].copy()
    return _hbar(d, "stock", BLUE_BAR, "Stock (MT)")
