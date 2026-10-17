"""Visual layer - matched 1:1 to the coal-dashboard.vercel.app design.

Palette, spacing and component styling come from that dashboard:
dark slate background, teal brand, flat cards, gradient header.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------ palette
BG = "#0b1220"
CARD = "#131c2e"
CARD2 = "#0f1a2b"
INK = "#e8eef8"
MUTED = "#94a3b8"
LINE = "#26334a"
BRAND = "#14b8a6"
BRAND2 = "#0e7490"
ACCENT = "#f59e0b"
TEAL = "#2dd4bf"
BLUE = "#60a5fa"
AMBER = "#fbbf24"
ROSE = "#fb7185"
VIOLET = "#a78bfa"
CYAN = "#22d3ee"
GRID = "rgba(148,163,184,.14)"
FONT = '"Segoe UI", Inter, system-ui, -apple-system, Arial, sans-serif'

CSS = """
<style>
  :root{
    --bg:#0b1220; --card:#131c2e; --card2:#0f1a2b; --ink:#e8eef8; --muted:#94a3b8; --line:#26334a;
    --brand:#14b8a6; --brand2:#0e7490; --accent:#f59e0b;
    --c1:#2dd4bf; --c2:#60a5fa; --c3:#fbbf24; --c4:#fb7185; --c5:#a78bfa; --c6:#22d3ee;
    --shadow:0 1px 2px rgba(0,0,0,.45), 0 12px 32px rgba(0,0,0,.35);
  }

  html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--ink) !important;
    font-family: "Segoe UI", Inter, system-ui, -apple-system, Arial, sans-serif !important;
  }

  /* remove Streamlit chrome - the reference has no sidebar/header */
  [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"],
  [data-testid="stDecoration"], [data-testid="stStatusWidget"], footer { display: none !important; }
  #MainMenu { visibility: hidden; }

  [data-testid="stMainBlockContainer"], .block-container {
    max-width: 1480px !important;
    padding: 4px 20px 40px !important;
  }
  [data-testid="stMainBlockContainer"] { margin: 0 auto; }

  /* tighten Streamlit's default vertical gaps to the reference rhythm */
  [data-testid="stVerticalBlock"] { gap: 0.85rem; }

  a { color: var(--brand); }

  /* ------------------------------------------------------------- header */
  header.top{
    display:flex; flex-wrap:wrap; gap:14px; align-items:center; justify-content:space-between;
    background:linear-gradient(120deg,#0f172a,#134e4a 60%,#155e75); color:#fff;
    border-radius:16px; padding:18px 22px; margin-bottom:22px;
    box-shadow:0 1px 2px rgba(0,0,0,.45), 0 12px 32px rgba(0,0,0,.35);
  }
  header.top .title h1{
    margin:0; font-size:20px; letter-spacing:.2px; font-weight:700; color:#fff;
    font-family:"Segoe UI", Inter, system-ui, -apple-system, Arial, sans-serif;
    line-height:1.3; padding:0;
  }
  header.top .title p{ margin:3px 0 0; color:#cbd5e1; font-size:12.5px; line-height:1.45; }
  header.top .title b{ color:#f1f5f9; }
  header.top .meta{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; justify-content:flex-end; }
  .pill{
    display:inline-flex; gap:7px; align-items:center; background:rgba(255,255,255,.12);
    border:1px solid rgba(255,255,255,.18); padding:6px 11px; border-radius:999px;
    font-size:12px; color:#e2e8f0; white-space:nowrap;
  }
  .dot{ width:8px; height:8px; border-radius:50%; background:#22c55e; box-shadow:0 0 0 4px rgba(34,197,94,.18); }

  /* ------------------------------------------------------------ filters */
  .filter-labels{
    font-size:11px; font-weight:600; letter-spacing:.4px; text-transform:uppercase;
    color:var(--muted); margin-bottom:-4px;
  }
  [data-testid="stWidgetLabel"] p{
    font-size:11px !important; font-weight:600 !important; letter-spacing:.4px !important;
    text-transform:uppercase; color:var(--muted) !important; margin-bottom:0 !important;
  }
  [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"].st-key-filterbar{
    padding:9px 16px !important;
  }
  /* Streamlit 1.66 uses react-aria comboboxes, not BaseWeb */
  [data-testid="stSelectbox"] [role="group"]{
    background:var(--card2) !important;
    border:1px solid var(--line) !important;
    border-radius:9px !important;
    min-height:38px !important;
    height:38px;
    padding:0 8px !important;
    box-shadow:none !important;
    transition:border-color .15s ease, box-shadow .15s ease;
  }
  [data-testid="stSelectbox"] [role="group"]:hover{ border-color:#33507a !important; }
  [data-testid="stSelectbox"] [role="group"]:focus-within{
    border-color:var(--brand) !important; box-shadow:0 0 0 3px rgba(20,184,166,.18) !important;
  }
  [data-testid="stSelectbox"] input[role="combobox"]{
    font-size:13.5px !important; color:var(--ink) !important; background:transparent !important;
    padding:0 2px !important;
  }
  [data-testid="stSelectbox"] button[aria-label="Open"]{ color:var(--muted) !important; }
  [data-testid="stSelectbox"] button[aria-label="Open"] svg{ fill:var(--muted) !important; }

  /* dropdown portal */
  [role="listbox"]{
    background:#182338 !important;
    border:1px solid var(--line) !important;
    border-radius:10px !important;
    box-shadow:0 1px 2px rgba(0,0,0,.45), 0 12px 32px rgba(0,0,0,.35) !important;
    padding:4px !important;
  }
  [role="option"]{
    padding:8px 10px !important; border-radius:7px !important;
    font-size:13px !important; color:var(--ink) !important; cursor:pointer;
  }
  [role="option"]:hover{ background:rgba(148,163,184,.12) !important; }
  [role="option"][aria-selected="true"]{
    background:rgba(20,184,166,.18) !important; color:#5eead4 !important; font-weight:600;
  }

  /* ------------------------------------------------------------- buttons */
  .stButton > button, .stDownloadButton > button{
    border-radius:9px !important; border:1px solid var(--line) !important;
    background:var(--card2) !important; color:var(--ink) !important;
    font-family:"Segoe UI", Inter, system-ui, sans-serif !important;
    font-size:13px !important; font-weight:600 !important; padding:.42rem 1rem !important;
    min-height:38px; transition:background .15s ease, border-color .15s ease;
  }
  .stButton > button:hover, .stDownloadButton > button:hover{ border-color:var(--brand) !important; }
  .stButton > button[kind="primary"]{
    background:var(--brand) !important; border-color:var(--brand) !important; color:#04211d !important;
    font-weight:700 !important;
  }
  .stButton > button[kind="primary"]:hover{ background:#0d9488 !important; border-color:#0d9488 !important; }

  /* --------------------------------------------------------- flat cards */
  [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]{
    background:var(--card) !important;
    border:1px solid var(--line) !important;
    border-radius:14px !important;
    padding:14px 16px 10px !important;
    box-shadow:0 1px 2px rgba(0,0,0,.45), 0 12px 32px rgba(0,0,0,.35) !important;
  }

  .card-head h3{
    margin:0 0 2px !important; padding:0 !important; font-size:14px; font-weight:700;
    color:var(--ink); font-family:"Segoe UI", Inter, system-ui, sans-serif;
    line-height:1.35 !important;
  }
  .card-head .sub{ font-size:11.5px; color:var(--muted); margin:0 0 6px 0; line-height:1.4; }

  /* ------------------------------------------------------------- KPIs */
  .kpis{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-bottom:20px; }
  .kpi{
    background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:15px 16px; box-shadow:0 1px 2px rgba(0,0,0,.45), 0 12px 32px rgba(0,0,0,.35);
    position:relative; overflow:hidden; min-height:90px;
  }
  .kpi::before{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--brand); }
  .kpi .k{ font-size:11px; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); font-weight:600; }
  .kpi .v{ font-size:25px; font-weight:700; margin-top:6px; letter-spacing:-.5px; color:var(--ink); line-height:1.2; }
  .kpi .u{ font-size:12px; color:var(--muted); font-weight:600; margin-left:3px; }
  .kpi .ctx{ font-size:11.5px; color:var(--muted); margin-top:3px; }

  /* ------------------------------------------------------------ footer */
  .defs{ margin-top:2px; color:var(--muted); font-size:11.5px; line-height:1.6; }
  .defs b{ color:#cbd5e1; }
  .defs i{ color:#cbd5e1; font-style:italic; }

  /* -------------------------------------------------------- plotly frame */
  [data-testid="stPlotlyChart"]{ border-radius:0; }
  .modebar{ display:none !important; }
  [data-testid="stCaptionContainer"], .stCaption{ color:var(--muted) !important; font-size:11px !important; }

  /* ----------------------------------------------------------- login */
  .login-brand{
    display:flex; align-items:center; gap:12px; justify-content:center; margin:9vh 0 14px 0;
  }
  .login-logo{
    width:44px; height:44px; border-radius:11px; display:grid; place-items:center;
    background:var(--brand); color:#04211d; font-weight:800; font-size:16px;
    letter-spacing:-.5px;
  }
  .login-name{ font-size:18px; font-weight:700; }
  .login-name span{ color:var(--brand); }
  [data-testid="stTextInput"] input{
    background:var(--card2) !important; border:1px solid var(--line) !important;
    border-radius:9px !important; color:var(--ink) !important; font-size:14px !important;
  }
  [data-testid="stTextInput"] input:focus{
    border-color:var(--brand) !important; box-shadow:0 0 0 3px rgba(20,184,166,.18) !important;
  }

  /* ------------------------------------------------------- data panel */
  .admin-note{ font-size:12px; color:var(--muted); line-height:1.6; }
  [data-testid="stExpander"]{
    border:1px solid var(--line) !important; border-radius:14px !important;
    background:var(--card) !important;
  }
  [data-testid="stExpander"] summary{ font-size:13px !important; color:var(--ink) !important; font-weight:600; }
  [data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  [data-testid="stFileUploaderDropzone"]{
    background:var(--card2) !important; border:1px dashed #33507a !important; border-radius:10px !important;
  }
  [data-baseweb="tab-list"]{ gap:6px; }
  [data-baseweb="tab"]{ font-size:12.5px !important; color:var(--muted) !important; }
  [data-baseweb="tab"][aria-selected="true"]{ color:var(--brand) !important; }

  /* --------------------------------------------------------- responsive */
  @media (max-width: 1080px){
    [data-testid="stHorizontalBlock"]{ flex-wrap:wrap !important; gap:12px !important; }
    [data-testid="stColumn"]{ flex:1 1 100% !important; min-width:100% !important; width:100% !important; }
    /* keep the filter bar to two columns like the reference */
    .st-key-filterbar [data-testid="stHorizontalBlock"]{ flex-wrap:wrap !important; }
    .st-key-filterbar [data-testid="stColumn"]{
      flex:1 1 46% !important; min-width:46% !important; width:46% !important;
    }
    [data-testid="stMainBlockContainer"], .block-container{ padding:14px 14px 32px !important; }
  }
  @media (max-width: 760px){
    .kpis{ grid-template-columns:1fr; }
    header.top{ padding:16px; }
  }
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------- components
def header(report_date: str, updated: str, live: bool = True) -> str:
    state = "Live" if live else "Snapshot"
    dot_bg = "#22c55e" if live else "#f59e0b"
    dot_shadow = "rgba(34,197,94,.18)" if live else "rgba(245,158,11,.18)"
    return (
        '<header class="top">'
        '<div class="title">'
        "<h1>Coal Market Dashboard</h1>"
        "<p>Live view of the <b>Master Database</b> &middot; stock (MT) &amp; "
        "quantity-weighted sale rates (BDT/MT)</p>"
        "</div>"
        '<div class="meta">'
        f'<span class="pill"><span class="dot" style="background:{dot_bg};'
        f'box-shadow:0 0 0 4px {dot_shadow}"></span> {state}</span>'
        f'<span class="pill">Report date {report_date}</span>'
        f'<span class="pill">Updated {updated}</span>'
        "</div>"
        "</header>"
    )


def kpi_cards(stock: str, rate: str) -> str:
    return (
        '<section class="kpis">'
        '<div class="kpi"><div class="k">Total stock</div>'
        f'<div class="v">{stock}<span class="u">MT</span></div></div>'
        '<div class="kpi"><div class="k">Avg sale rate</div>'
        f'<div class="v">{rate}<span class="u">BDT/MT</span></div></div>'
        "</section>"
    )


def card_head(title: str, sub: str) -> str:
    return f'<div class="card-head"><h3>{title}</h3><div class="sub">{sub}</div></div>'


def footer() -> str:
    return (
        '<div class="defs"><b>Definitions.</b> Stock = sum of <i>Quantity (MT)</i>. '
        "Avg sale rate = quantity-weighted average of <i>Sale / Retail Rate</i>, "
        "ignoring zero/blank rates. Avg stock per entry = mean of <i>Quantity</i> over "
        "entries with stock &gt; 0. Data comes from the Excel <i>Master Database</i> sheet."
        "<br>Weekly uploads and data health are in the panel below.</div>"
    )


# ---------------------------------------------------------------- plotly
def style_fig(fig: go.Figure, height: int = 265) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=MUTED, size=11),
        margin=dict(l=6, r=10, t=18, b=6),
        showlegend=False,
        barcornerradius=5,
        hoverlabel=dict(bgcolor="#182338", bordercolor=LINE,
                        font=dict(family=FONT, size=12, color=INK)),
    )
    fig.update_xaxes(
        gridcolor=GRID, zeroline=False, linecolor=GRID,
        tickfont=dict(size=11, color=MUTED), tickformat=",.0f", nticks=9,
        title_font=dict(size=11, color=MUTED),
    )
    fig.update_yaxes(
        gridcolor=GRID, zeroline=False, linecolor=GRID,
        tickfont=dict(size=11, color=MUTED), tickformat=",.0f", nticks=9,
        title_font=dict(size=11, color=MUTED),
    )
    return fig
