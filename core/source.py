"""Live data connection to the Google Sheet, with a local snapshot fallback."""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

import config


class SourceError(RuntimeError):
    """Raised when the sheet cannot be read."""


def sheet_urls(sheet_id: str | None = None) -> tuple[str | None, str]:
    """Return (csv_url, xlsx_url) for a workbook. csv_url needs a configured gid."""
    sid = sheet_id or config.SHEET_ID
    base = f"https://docs.google.com/spreadsheets/d/{sid}"
    csv_url = (
        f"{base}/export?format=csv&gid={config.MASTER_GID}"
        if config.MASTER_GID is not None
        else None
    )
    xlsx_url = f"{base}/export?format=xlsx"
    return csv_url, xlsx_url


def candidate_sheet_ids() -> list[str]:
    ids = [config.SHEET_ID, *getattr(config, "SHEET_FALLBACKS", [])]
    return list(dict.fromkeys(i for i in ids if i))


def _get(url: str) -> bytes:
    resp = requests.get(
        url,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "Mozilla/5.0 (coal-dashboard)"},
    )
    if resp.status_code != 200:
        raise SourceError(f"Google returned HTTP {resp.status_code}")
    body = resp.content
    if len(body) < 200:
        raise SourceError("Google returned an empty file")
    head = body[:600].lstrip().lower()
    if head.startswith(b"<") or b"<html" in head:
        raise SourceError("Google returned a sign-in page (link is not public)")
    return body


def _read_body(body: bytes) -> pd.DataFrame:
    if body[:2] == b"PK":  # xlsx / zip
        book = pd.ExcelFile(io.BytesIO(body))
        sheet = (
            config.MASTER_SHEET_NAME
            if config.MASTER_SHEET_NAME in book.sheet_names
            else book.sheet_names[0]
        )
        return book.parse(sheet, header=0)
    return pd.read_csv(io.BytesIO(body), encoding="utf-8-sig")


def fetch_master() -> tuple[pd.DataFrame, dict]:
    """Download the Master Database tab. Returns (dataframe, metadata).

    Tries the primary workbook first, then any configured fallbacks. A private
    or deleted file is skipped instead of breaking the dashboard.
    """
    errors: list[str] = []
    for sid in candidate_sheet_ids():
        csv_url, xlsx_url = sheet_urls(sid)
        candidates: list[tuple[str, str]] = []
        if csv_url:
            candidates.append(("Google Sheet · CSV", csv_url))
        candidates.append(("Google Sheet · Excel export", xlsx_url))

        for label, url in candidates:
            try:
                body = _get(url)
                df = _read_body(body)
                if df.empty:
                    raise SourceError("sheet came back empty")
                return df, {
                    "source": label,
                    "sheet_id": sid,
                    "fetched_at": datetime.now(timezone.utc),
                    "live": True,
                    "note": "",
                }
            except Exception as exc:  # try the next transport / next file
                errors.append(f"{sid[:10]}… {label}: {exc}")

    raise SourceError(" | ".join(errors))


def read_snapshot() -> tuple[pd.DataFrame, dict]:
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.LOCAL_SNAPSHOT)
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df, {
        "source": "Local snapshot (offline)",
        "sheet_id": None,
        "fetched_at": datetime.fromtimestamp(os.path.getmtime(path), timezone.utc),
        "live": False,
        "note": "",
    }


@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner=False)
def _load_cached(force_local: bool = False) -> tuple[pd.DataFrame, dict]:
    if force_local or os.environ.get("COAL_SNAPSHOT_ONLY") == "1":
        return read_snapshot()
    try:
        return fetch_master()
    except Exception as exc:
        df, meta = read_snapshot()
        meta["note"] = (
            "Could not reach Google Sheets, so the bundled snapshot is shown. "
            f"Details: {exc}"
        )
        return df, meta


def load_master(force_local: bool = False) -> tuple[pd.DataFrame, dict]:
    return _load_cached(force_local)


def clear_cache() -> None:
    _load_cached.clear()


def age_label(fetched_at: datetime) -> str:
    seconds = max(0, int((datetime.now(timezone.utc) - fetched_at).total_seconds()))
    if seconds < 90:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    return f"{hours // 24} d ago"
