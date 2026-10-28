"""Coal Market Dashboard - Streamlit edition of coal-dashboard.vercel.app."""

from __future__ import annotations

import hmac

import streamlit as st

st.set_page_config(
    page_title="Coal Market Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import config  # noqa: E402
from core import charts, filters, source, theme, transform  # noqa: E402
from views import admin  # noqa: E402


def _app_password() -> str | None:
    try:
        value = st.secrets["app"].get("password")
        return str(value) if value else None
    except Exception:
        return None


def _authenticated() -> bool:
    if _app_password() is None:
        return True
    return bool(st.session_state.get("authed"))


def _login_screen() -> None:
    st.markdown(
        '<div class="login-brand"><div class="login-logo">CM</div>'
        '<div class="login-name">Coal Market <span>Dashboard</span></div></div>',
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 1.05, 1])
    with mid:
        with st.container(border=True):
            st.markdown("#### Team access")
            st.caption("Enter the shared password to open the dashboard.")
            password = st.text_input(
                "Password", type="password", key="login_pw",
                label_visibility="collapsed", placeholder="Password",
            )
            if st.button("Enter dashboard", type="primary", width="stretch"):
                if hmac.compare_digest(password, _app_password() or ""):
                    st.session_state["authed"] = True
                    st.rerun()
                else:
                    st.error("Wrong password.")


def _updated_label(ts) -> str:
    local = ts.astimezone()
    hour = local.strftime("%I").lstrip("0") or "12"
    return f"{local.month}/{local.day}/{local.year}, {hour}:{local:%M:%S %p}"


def _chart_card(title: str, sub: str, fig, key: str) -> None:
    with st.container(border=True):
        st.markdown(theme.card_head(title, sub), unsafe_allow_html=True)
        st.plotly_chart(
            fig, width="stretch", config={"displayModeBar": False}, key=key
        )


@st.fragment(run_every=config.AUTO_REFRESH_SECONDS)
def _dashboard() -> None:
    """Everything visual lives in a fragment so it can refresh itself."""
    raw, meta = source.load_master()
    try:
        df = transform.prepare(raw)
        quality = transform.date_quality(df)
    except Exception as exc:
        st.error(f"Could not read the Master Database: {exc}")
        return

    if quality.empty:
        st.error(
            "No dated rows were found in the Master Database. Check that column A holds "
            "the report date and that the header row is row 1."
        )
        return

    header_slot = st.empty()
    ctx = filters.render(df, quality)
    ctx["raw"] = df
    d = ctx["df"]

    k = transform.kpis(d)
    updated = _updated_label(meta["fetched_at"])
    header_slot.markdown(
        theme.header(
            ctx["date"].strftime("%Y-%m-%d"),
            updated,
            live=bool(meta.get("live")),
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        theme.kpi_cards(transform.fmt_int(k["stock"]), transform.fmt_rate2(k["avg_rate"])),
        unsafe_allow_html=True,
    )

    by_loc = transform.by_location(d)
    by_org = transform.by_origin(d)
    by_imp = transform.by_importer(d)

    row1_left, row1_right = st.columns(2, gap="small")
    with row1_left:
        _chart_card(
            "Location-wise Stock Quantity",
            "Total stock (MT) per dumping point",
            charts.location_stock(by_loc),
            "chart_location",
        )
    with row1_right:
        _chart_card(
            "Origin-wise — Avg Stock &amp; Avg Sale Rate",
            "Bars: average stock per importer (MT) &middot; "
            "Line: weighted avg sale rate (BDT/MT)",
            charts.origin_combo(by_org),
            "chart_origin",
        )

    row2_left, row2_right = st.columns(2, gap="small")
    with row2_left:
        _chart_card(
            "Importer — Average Sale Rate",
            "Quantity-weighted avg sale rate (BDT/MT)",
            charts.importer_rates(by_imp),
            "chart_importer_rate",
        )
    with row2_right:
        _chart_card(
            "Importer-wise Stock Quantity",
            "Total stock (MT) per importer",
            charts.importer_stock(by_imp),
            "chart_importer_stock",
        )

    st.markdown(theme.footer(), unsafe_allow_html=True)

    if not meta.get("live"):
        st.caption(
            "Snapshot mode: Google Sheets could not be reached, so the bundled copy is shown."
        )

    st.session_state["ctx"] = ctx
    st.session_state["meta"] = meta


def main() -> None:
    theme.inject()

    if not _authenticated():
        _login_screen()
        st.stop()

    _dashboard()

    ctx = st.session_state.get("ctx")
    meta = st.session_state.get("meta")
    if ctx and meta:
        with st.expander(
            "Weekly upload & data health",
            expanded=bool(st.session_state.get("_admin_open")),
        ):
            admin.render(ctx, meta)


main()
