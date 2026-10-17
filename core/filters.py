"""Top filter bar - five searchable selects + reset, as in the reference."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from core import transform

ALL = "__all__"


def _all_label(name: str):
    return f"All {name}"


def _reset_all(default: pd.Timestamp) -> None:
    """Runs before widgets are created, so widget keys may be reassigned."""
    st.session_state["f_date"] = default
    st.session_state["f_loc"] = ALL
    st.session_state["f_imp"] = ALL
    st.session_state["f_org"] = ALL
    st.session_state["f_rem"] = ALL


def render(df: pd.DataFrame, quality: pd.DataFrame) -> dict:
    valid = transform.analysis_rows(df)

    dates = sorted(quality.index, reverse=True)
    if config.DEFAULT_TO_LATEST_DATE:
        default = dates[0] if dates else None
    else:
        default = transform.default_date(quality) or (dates[0] if dates else None)

    locations = sorted(valid["location"].unique())
    importers = sorted(valid["importer"].unique())
    origins = sorted(valid["origin"].replace("", "(unknown)").unique())
    remarks = sorted(valid["remarks"].replace("", "(blank)").unique())

    def date_label(d: pd.Timestamp) -> str:
        label = d.strftime("%Y-%m-%d")
        if d in quality.index and not bool(quality.loc[d, "complete"]):
            return f"{label} · in progress"
        return label

    with st.container(border=True, key="filterbar"):
        c0, c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1, 0.9], vertical_alignment="bottom")

        with c0:
            date_kwargs = {}
            if "f_date" not in st.session_state:
                date_kwargs["index"] = dates.index(default)
            sel_date = st.selectbox(
                "Date", dates, format_func=date_label,
                key="f_date", label_visibility="visible", **date_kwargs,
            )
        with c1:
            sel_loc = st.selectbox(
                "Location", [ALL] + locations,
                format_func=lambda v: _all_label("locations") if v == ALL else v,
                key="f_loc",
            )
        with c2:
            sel_imp = st.selectbox(
                "Importer", [ALL] + importers,
                format_func=lambda v: _all_label("importers") if v == ALL else v,
                key="f_imp",
            )
        with c3:
            sel_org = st.selectbox(
                "Origin", [ALL] + origins,
                format_func=lambda v: _all_label("origins") if v == ALL else v,
                key="f_org",
            )
        with c4:
            sel_rem = st.selectbox(
                "Remarks", [ALL] + remarks,
                format_func=lambda v: _all_label("remarks") if v == ALL else v,
                key="f_rem",
            )
        with c5:
            st.button(
                "Reset filters", type="primary", width="stretch",
                on_click=_reset_all, args=(default,),
            )

    d = valid[valid["date"] == sel_date].copy()
    if sel_loc != ALL:
        d = d[d["location"] == sel_loc]
    if sel_imp != ALL:
        d = d[d["importer"] == sel_imp]
    if sel_org != ALL:
        origin_series = d["origin"].replace("", "(unknown)")
        d = d[origin_series == sel_org]
    if sel_rem != ALL:
        remark_series = d["remarks"].replace("", "(blank)")
        d = d[remark_series == sel_rem]

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
