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


def sheet_urls() -> tuple[str | None, str]:
    """Return (csv_url, xlsx_url). csv_url is None when no gid is configured."""
    base = f"https://docs.google.com/spreadsheets/d/{config.SHEET_ID}"
    csv_url = (
        f"{base}/export?format=csv&gid={config.MASTER_GID}"
        if config.MASTER_GID is not None
        else None
    )
    xlsx_url = f"{base}/export?format=xlsx"
    return csv_url, xlsx_url


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
        return pd.read_excel(
            io.BytesIO(body), sheet_name=config.MASTER_SHEET_NAME, header=0
        )
    return pd.read_csv(io.BytesIO(body), encoding="utf-8-sig")


def fetch_master() -> tuple[pd.DataFrame, dict]:
    """Download the Master Database tab. Returns (dataframe, metadata)."""
    csv_url, xlsx_url = sheet_urls()
    candidates: list[tuple[str, str]] = []
    if csv_url:
        candidates.append(("Google Sheet · CSV", csv_url))
    candidates.append(("Google Sheet · Excel export", xlsx_url))

    errors: list[str] = []
    for label, url in candidates:
        try:
            body = _get(url)
            df = _read_body(body)
            if df.empty:
                raise SourceError("sheet came back empty")
            return df, {
                "source": label,
                "fetched_at": datetime.now(timezone.utc),
                "live": True,
                "note": "",
            }
        except Exception as exc:  # try the next transport
            errors.append(f"{label}: {exc}")

    raise SourceError(" | ".join(errors))


def read_snapshot() -> tuple[pd.DataFrame, dict]:
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.LOCAL_SNAPSHOT)
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df, {
        "source": "Local snapshot (offline)",
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
