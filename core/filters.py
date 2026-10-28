"""Top filter bar - five searchable selects + reset.

All chart data is scoped to ONE report date. The other filter options are built
from that same date, so a location/importer that only exists on another day is
never offered.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from core import transform

ALL = "__all__"


def _all_label(name: str):
    return f"All {name}"


def _reset_dependent() -> None:
    """Called before the script when the date changes."""
    for key in ("f_loc", "f_imp", "f_org", "f_rem"):
        st.session_state[key] = ALL


def _reset_all(default: pd.Timestamp) -> None:
    """Reset button callback - runs before widgets are created."""
    st.session_state["f_date"] = default
    for key in ("f_loc", "f_imp", "f_org", "f_rem"):
        st.session_state[key] = ALL


def _prune(key: str, options: list[str]) -> None:
    if st.session_state.get(key) not in options:
        st.session_state[key] = ALL


def render(df: pd.DataFrame, quality: pd.DataFrame) -> dict:
    valid = transform.analysis_rows(df)

    dates = sorted(quality.index, reverse=True)
    if not dates:
        return {"date": None, "df": valid.iloc[0:0], "quality": quality,
                "all_valid": valid, "filters": {}, "in_progress": False}

    if config.DEFAULT_TO_LATEST_DATE:
        default = dates[0]
    else:
        default = transform.default_date(quality) or dates[0]

    def date_label(d: pd.Timestamp) -> str:
        return d.strftime("%Y-%m-%d")

    with st.container(border=True, key="filterbar"):
        c0, c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1, 0.9], vertical_alignment="bottom")

        with c0:
            date_kwargs = {}
            if "f_date" not in st.session_state:
                date_kwargs["index"] = dates.index(default)
            sel_date = st.selectbox(
                "Date (type to search)", dates, format_func=date_label,
                key="f_date", label_visibility="visible",
                help="Click the box and type a date to search.",
                on_change=_reset_dependent,
                **date_kwargs,
            )

        # Options come from the selected day only - daily data, no cross-date lists.
        base = valid[valid["date"] == sel_date].copy()
        locations = sorted(base["location"].unique())
        importers = sorted(base["importer"].unique())
        origins = sorted(base["origin"].replace("", "(unknown)").unique())
        remarks = sorted(base["remarks"].replace("", "(blank)").unique())

        loc_options = [ALL] + locations
        imp_options = [ALL] + importers
        org_options = [ALL] + origins
        rem_options = [ALL] + remarks

        for key, options in (("f_loc", loc_options), ("f_imp", imp_options),
                             ("f_org", org_options), ("f_rem", rem_options)):
            _prune(key, options)

        with c1:
            sel_loc = st.selectbox(
                "Location", loc_options,
                format_func=lambda v: _all_label("locations") if v == ALL else v,
                key="f_loc",
            )
        with c2:
            sel_imp = st.selectbox(
                "Importer", imp_options,
                format_func=lambda v: _all_label("importers") if v == ALL else v,
                key="f_imp",
            )
        with c3:
            sel_org = st.selectbox(
                "Origin", org_options,
                format_func=lambda v: _all_label("origins") if v == ALL else v,
                key="f_org",
            )
        with c4:
            sel_rem = st.selectbox(
                "Remarks", rem_options,
                format_func=lambda v: _all_label("remarks") if v == ALL else v,
                key="f_rem",
            )
        with c5:
            st.button(
                "Reset filters", type="primary", width="stretch",
                on_click=_reset_all, args=(default,),
            )

    d = base
    if sel_loc != ALL:
        d = d[d["location"] == sel_loc]
    if sel_imp != ALL:
        d = d[d["importer"] == sel_imp]
    if sel_org != ALL:
        d = d[d["origin"].replace("", "(unknown)") == sel_org]
    if sel_rem != ALL:
        d = d[d["remarks"].replace("", "(blank)") == sel_rem]

    return {
        "date": sel_date,
        "df": d,
        "quality": quality,
        "all_valid": valid,
        "filters": {
            "date": sel_date, "location": sel_loc, "importer": sel_imp,
            "origin": sel_org, "remarks": sel_rem,
        },
    }
