"""Optional write-back: append a validated weekly file to the live Google Sheet.

Requires a Google service account (see README) and a *native* Google Sheet.
Reading the dashboard never needs this - it only powers the upload page.
"""

from __future__ import annotations

import math
from datetime import date, datetime

import pandas as pd
import streamlit as st

import config


def _sa_info() -> dict | None:
    try:
        info = st.secrets["gcp_service_account"]
        return dict(info)
    except Exception:
        return None


def is_configured() -> bool:
    return _sa_info() is not None


def service_account_email() -> str:
    info = _sa_info() or {}
    return str(info.get("client_email", ""))


def friendly_error(exc: Exception) -> str:
    text = str(exc)
    low = text.lower()
    email = service_account_email() or "your service-account email"
    if "not a google sheet" in low or "spreadsheetnotfound" in low or "404" in low:
        return (
            "The dashboard cannot write to this file yet. It is still an Excel "
            "(.xlsx) file in Drive. Open it in Google Sheets and use "
            "File → Save as Google Sheets, then put the new file id in config.py. "
            f"Also share it with {email} as Editor."
        )
    if "403" in low or "permission" in low or "forbidden" in low:
        return f"No write permission. Share the Google Sheet with {email} as Editor."
    if "quota" in low or "429" in low:
        return "Google rate limit hit. Wait a minute and try again."
    return text


def _worksheet():
    import gspread

    info = _sa_info()
    if not info:
        raise RuntimeError("No service account configured in secrets.")
    client = gspread.service_account_from_dict(info)
    return client.open_by_key(config.SHEET_ID).worksheet(config.MASTER_SHEET_NAME)


def test_connection() -> tuple[bool, str]:
    if not is_configured():
        return False, "No service account in .streamlit/secrets.toml"
    try:
        ws = _worksheet()
        return True, f"Connected · '{ws.title}' has {ws.row_count:,} rows"
    except Exception as exc:
        return False, friendly_error(exc)


def _next_free_row(ws) -> int:
    """First row after the last row that has a date in column A."""
    col_a = ws.col_values(1)
    last = 0
    for i, value in enumerate(col_a, start=1):
        if str(value).strip():
            last = i
    return max(last + 1, 2)


def _cell(value) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _num(value) -> str | float:
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return ""
    if math.isnan(f):
        return ""
    return f


def build_values(df: pd.DataFrame, start_row: int) -> list[list]:
    rows: list[list] = []
    for offset, (_, row) in enumerate(df.iterrows()):
        r = start_row + offset
        prev = r - 1
        upcoming_formula = config.UPCOMING_NO_FORMULA.format(r=r, prev=prev)
        is_upcoming_formula = config.IS_UPCOMING_FORMULA.format(r=r)

        def optional(field: str):
            value = _num(row[field])
            if isinstance(value, float) and value <= 0:
                return ""
            return value

        rows.append([
            _cell(row["date"]),
            _cell(row["location"]),
            _cell(row["importer_sheet"]),
            _cell(row["origin"]),
            _cell(row["grade"]),
            _cell(row["mine"]),
            _num(row["quantity"]),
            optional("purchase_rate"),
            _num(row["sale_rate"]),
            _cell(row["status"]),
            _cell(row["remarks"]),
            _cell(row["vessel"]),
            optional("vessel_qty"),
            upcoming_formula,
            is_upcoming_formula,
        ])
    return rows


def append_rows(df: pd.DataFrame) -> tuple[bool, str]:
    """Write validated rows into the Master Database. Returns (ok, message)."""
    if df.empty:
        return False, "Nothing to upload."
    try:
        ws = _worksheet()
        start = _next_free_row(ws)
        values = build_values(df, start)
        end = start + len(values) - 1
        if end > ws.row_count:
            ws.add_rows(end - ws.row_count + 5)
        ws.update(
            values=values,
            range_name=f"A{start}:O{end}",
            value_input_option="USER_ENTERED",
        )
        return True, f"Added {len(values)} rows at A{start}:O{end}."
    except Exception as exc:
        return False, friendly_error(exc)


def existing_keys(ws=None) -> set[tuple]:
    """Keys used to stop the same week being uploaded twice."""
    try:
        ws = ws or _worksheet()
        records = ws.get_all_values()
    except Exception:
        return set()
    keys: set[tuple] = set()
    for row in records[1:]:
        if len(row) < 9 or not str(row[0]).strip():
            continue
        def norm(v: str) -> str:
            try:
                return f"{float(str(v).replace(',', '')):.2f}"
            except ValueError:
                return str(v).strip().lower()
        remarks = str(row[10]).strip().lower() if len(row) > 10 else ""
        vessel = str(row[11]).strip().lower() if len(row) > 11 else ""
        keys.add((
            str(row[0]).strip(),
            str(row[1]).strip().lower(),
            str(row[2]).strip().lower(),
            str(row[3]).strip().lower(),
            norm(row[6]),
            norm(row[8]),
            remarks,
            vessel,
        ))
    return keys


def key_for_row(row: pd.Series) -> tuple:
    return (
        pd.Timestamp(row["date"]).strftime("%Y-%m-%d") if pd.notna(row["date"]) else "",
        str(row["location"]).strip().lower(),
        str(row["importer_sheet"]).strip().lower(),
        str(row["origin"]).strip().lower(),
        f"{float(row['quantity']):.2f}",
        f"{float(row['sale_rate']):.2f}",
        str(row["remarks"]).strip().lower(),
        str(row["vessel"]).strip().lower(),
    )
