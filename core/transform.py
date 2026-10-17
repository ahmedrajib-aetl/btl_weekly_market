"""Reading, cleaning and aggregating the market data.

House rules that this module enforces:
  * one report date = one market snapshot. Stock is NEVER summed across dates.
  * rows with no Location or no Importer are incomplete data entry, not stock.
  * sale rate averages are quantity-weighted and ignore zero/blank rates,
    exactly like the workbook's own Report sheet.
"""

from __future__ import annotations

import difflib
import math
import re

import numpy as np
import pandas as pd

import config

# ------------------------------------------------------------------ columns
HEADER_ALIASES: dict[str, list[str]] = {
    "date": ["date", "reportdate", "week", "weekdate", "reportingdate"],
    "location": ["location", "dumpingpoint", "dumpingpointlocation", "point", "port", "destination"],
    "importer": ["importer", "importername", "company", "buyer", "party"],
    "origin": ["origin", "country", "sourcecountry", "originofcoal"],
    "grade": ["coalgradecal", "coalgrade", "grade", "cal", "calorificvalue"],
    "mine": ["mine", "colliery"],
    "quantity": ["quantitymt", "quantity", "stockmt", "stock", "qtymt", "qty"],
    "purchase_rate": ["bulkpurchaseratebdtmt", "bulkpurchaserate", "purchaserate", "buyrate"],
    "sale_rate": ["saleretailratebdtmt", "saleretailrate", "salerate", "retailrate", "rate"],
    "status": ["status"],
    "remarks": ["remarks", "remark", "note", "notes", "category"],
    "vessel": ["vesselname", "vessel"],
    "vessel_qty": ["vesselqtymt", "vesselqty", "vesselquantity"],
    "upcoming_no": ["upcomingnoauto", "upcomingno", "upcoming"],
    "is_upcoming": ["isupcomingauto", "isupcoming"],
}

TEXT_FIELDS = ["location", "importer", "origin", "grade", "mine", "status", "remarks",
               "vessel"]
NUM_FIELDS = ["quantity", "purchase_rate", "sale_rate", "vessel_qty", "upcoming_no",
              "is_upcoming"]

UPCOMING_STATUS = {"in-transit", "in transit", "expected", "delayed"}


def _key(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    s = str(value).strip()
    if s.lower() in {"nan", "nat", "none", "-", "--", "n/a"}:
        return ""
    return re.sub(r"\s+", " ", s)


def _num(value: object) -> float:
    if value is None:
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value) if not pd.isna(value) else np.nan
    s = str(value).strip().replace(",", "").replace(" ", "")
    s = re.sub(r"(mt|bdt|/|tk|kg)", "", s, flags=re.I)
    if s in {"", "-", "--", "nan", "n/a"}:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def _date_one(value: object) -> pd.Timestamp:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).normalize()
    if isinstance(value, (int, float, np.integer, np.floating)):
        n = float(value)
        if 20000 <= n <= 80000:  # Excel serial date
            return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)).normalize()
        return pd.NaT
    s = str(value).strip()
    if s.lower() in {"", "-", "nan", "nat", "none"}:
        return pd.NaT
    if re.fullmatch(r"\d{5}(\.0+)?", s):  # serial stored as text
        return _date_one(float(s))
    # ISO dates must NOT be parsed day-first ("2026-10-11" is 11 Oct, not 10 Nov).
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", s):
        ts = pd.to_datetime(s, errors="coerce", dayfirst=False)
    else:
        ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return pd.Timestamp(ts).normalize() if not pd.isna(ts) else pd.NaT


def _find_columns(raw: pd.DataFrame) -> dict[str, str]:
    keys = {_key(c): c for c in raw.columns}
    found: dict[str, str] = {}
    used: set[str] = set()
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in keys and keys[alias] not in used:
                found[field] = keys[alias]
                used.add(keys[alias])
                break
        if field in found:
            continue
        for k, original in keys.items():
            if original in used:
                continue
            if any(alias in k for alias in aliases):
                found[field] = original
                used.add(original)
                break
    return found


def prepare(raw: pd.DataFrame, apply_aliases: bool = True) -> pd.DataFrame:
    """Turn the sheet into a clean, typed frame (one row per sheet row)."""
    if raw is None or raw.empty:
        raise ValueError("The Master Database tab is empty.")

    raw = raw.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    cols = _find_columns(raw)
    if "date" not in cols:
        raise ValueError(
            "No 'Date' column found in Master Database. Expected the header in row 1."
        )

    out = pd.DataFrame(index=raw.index)
    out["date"] = raw[cols["date"]].map(_date_one)

    for field in TEXT_FIELDS:
        if field in cols:
            out[field] = raw[cols[field]].map(_text)
        else:
            out[field] = ""

    for field in NUM_FIELDS:
        if field in cols:
            out[field] = raw[cols[field]].map(_num)
        else:
            out[field] = np.nan

    out["importer_sheet"] = out["importer"]

    if apply_aliases and config.IMPORTER_ALIASES:
        out["importer"] = out["importer"].replace(config.IMPORTER_ALIASES)

    # Fill numbers so arithmetic never sees NaN.
    for field in ("quantity", "purchase_rate", "sale_rate", "vessel_qty"):
        out[field] = out[field].fillna(0.0).clip(lower=0)

    out["is_complete_row"] = (
        out["date"].notna() & out["location"].ne("") & out["importer"].ne("")
    )

    status_key = out["status"].str.lower().str.strip()
    remarks_key = out["remarks"].str.lower()
    out["upcoming"] = (
        (out["is_upcoming"].fillna(0) >= 1)
        | status_key.isin(UPCOMING_STATUS)
        | remarks_key.str.contains("upcoming", na=False)
    )

    out["has_stock"] = out["quantity"] > 0
    out["rate_ok"] = (out["quantity"] > 0) & (out["sale_rate"] > 0)
    out["weighted_value"] = np.where(out["rate_ok"], out["quantity"] * out["sale_rate"], 0.0)
    out["weight"] = np.where(out["rate_ok"], out["quantity"], 0.0)

    return out.sort_values(["date", "location", "importer"]).reset_index(drop=True)


def analysis_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["is_complete_row"]].copy()


# -------------------------------------------------------------- date quality
def date_quality(df: pd.DataFrame) -> pd.DataFrame:
    """Per report date: how many rows are usable, stock, completeness verdict."""
    dated = df[df["date"].notna()]
    if dated.empty:
        return pd.DataFrame(columns=["rows_total", "rows_valid", "importers", "stock", "complete"])

    valid = dated[dated["is_complete_row"]]
    q = dated.groupby("date").agg(rows_total=("date", "size"))
    q["rows_valid"] = valid.groupby("date").size().reindex(q.index, fill_value=0)
    q["importers"] = valid.groupby("date")["importer"].nunique().reindex(q.index, fill_value=0)
    q["stock"] = valid.groupby("date")["quantity"].sum().reindex(q.index, fill_value=0.0)
    peak = q["rows_valid"].max()
    threshold = max(config.MIN_ROWS_FOR_COMPLETE, math.ceil(peak * config.COMPLETENESS_RATIO))
    q["complete"] = q["rows_valid"] >= threshold
    q["threshold"] = threshold
    return q.sort_index()


def complete_dates(quality: pd.DataFrame) -> list[pd.Timestamp]:
    if quality.empty:
        return []
    return [d for d in quality.index if bool(quality.loc[d, "complete"])]


def default_date(quality: pd.DataFrame) -> pd.Timestamp | None:
    dates = complete_dates(quality)
    return dates[-1] if dates else (quality.index.max() if len(quality) else None)


def previous_date(quality: pd.DataFrame, current: pd.Timestamp) -> pd.Timestamp | None:
    earlier = [d for d in complete_dates(quality) if d < current]
    return earlier[-1] if earlier else None


# ------------------------------------------------------------- aggregations
def _wavg(frame: pd.DataFrame) -> float:
    weight = frame["weight"].sum()
    if weight <= 0:
        return float("nan")
    return float(frame["weighted_value"].sum() / weight)


def kpis(d: pd.DataFrame, prev: pd.DataFrame | None = None) -> dict:
    stock = float(d["quantity"].sum())
    rate = _wavg(d)
    out = {
        "stock": stock,
        "importers": int(d["importer"].nunique()),
        "locations": int(d["location"].nunique()),
        "origins": int(d["origin"].replace("", np.nan).nunique()),
        "avg_rate": rate,
        "entries": int(d["has_stock"].sum()),
        "upcoming": int(d["upcoming"].sum()),
        "stock_delta": None,
        "rate_delta": None,
    }
    if prev is not None and not prev.empty:
        prev_stock = float(prev["quantity"].sum())
        if prev_stock > 0:
            out["stock_delta"] = (stock - prev_stock) / prev_stock * 100
        prev_rate = _wavg(prev)
        if not math.isnan(prev_rate) and prev_rate > 0 and not math.isnan(rate):
            out["rate_delta"] = (rate - prev_rate) / prev_rate * 100
    return out


def by_location(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("location", dropna=False)
    out = pd.DataFrame({
        "stock": g["quantity"].sum(),
        "entries": g["has_stock"].sum(),
        "importers": g["importer"].nunique(),
        "upcoming": g["upcoming"].sum(),
        "weighted_value": g["weighted_value"].sum(),
        "weight": g["weight"].sum(),
    })
    out["avg_rate"] = np.where(out["weight"] > 0, out["weighted_value"] / out["weight"].replace(0, np.nan), np.nan)
    out["share"] = out["stock"] / out["stock"].sum() if out["stock"].sum() else 0
    return out.sort_values("stock", ascending=False)


def by_origin(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("origin", dropna=False)
    out = pd.DataFrame({
        "stock": g["quantity"].sum(),
        "entries": g["has_stock"].sum(),
        "importers": g["importer"].nunique(),
        "locations": g["location"].nunique(),
        "upcoming": g["upcoming"].sum(),
        "weighted_value": g["weighted_value"].sum(),
        "weight": g["weight"].sum(),
    })
    out["avg_rate"] = np.where(out["weight"] > 0, out["weighted_value"] / out["weight"].replace(0, np.nan), np.nan)
    out["avg_stock_per_importer"] = np.where(out["importers"] > 0, out["stock"] / out["importers"], np.nan)
    # Reference definition: mean quantity over entries that actually carry stock.
    out["avg_stock_per_entry"] = np.where(out["entries"] > 0, out["stock"] / out["entries"], 0.0)
    out["share"] = out["stock"] / out["stock"].sum() if out["stock"].sum() else 0
    rates = d[d["sale_rate"] > 0].groupby("origin")["sale_rate"].agg(["min", "max"])
    out = out.join(rates)
    return out.sort_values("stock", ascending=False)


def by_importer(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("importer", dropna=False)
    out = pd.DataFrame({
        "stock": g["quantity"].sum(),
        "entries": g["has_stock"].sum(),
        "locations": g["location"].nunique(),
        "origins": g["origin"].nunique(),
        "upcoming": g["upcoming"].sum(),
        "weighted_value": g["weighted_value"].sum(),
        "weight": g["weight"].sum(),
    })
    out["avg_rate"] = np.where(out["weight"] > 0, out["weighted_value"] / out["weight"].replace(0, np.nan), np.nan)
    out["share"] = out["stock"] / out["stock"].sum() if out["stock"].sum() else 0
    out["origin_mix"] = d.groupby("importer")["origin"].apply(
        lambda s: ", ".join(sorted({v for v in s if v}))
    )
    out["location_mix"] = d.groupby("importer")["location"].apply(
        lambda s: ", ".join(sorted({v for v in s if v}))
    )
    return out.sort_values("stock", ascending=False)


def stock_matrix(d: pd.DataFrame, row: str = "importer", col: str = "origin") -> pd.DataFrame:
    return d.pivot_table(index=row, columns=col, values="quantity", aggfunc="sum", fill_value=0.0)


def rate_matrix(d: pd.DataFrame, row: str = "location", col: str = "origin") -> pd.DataFrame:
    return d.pivot_table(index=row, columns=col, values="sale_rate", aggfunc="mean")


def remarks_split(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(d["remarks"].replace("", "No remarks"))
    out = pd.DataFrame({
        "stock": g["quantity"].sum(),
        "rows": g.size(),
        "upcoming": g["upcoming"].sum(),
    })
    return out.sort_values("stock", ascending=False)


def trend(df: pd.DataFrame, quality: pd.DataFrame) -> pd.DataFrame:
    """One point per complete report date (stock is a snapshot, not a sum)."""
    valid = analysis_rows(df)
    dates = complete_dates(quality)
    rows = []
    for d in dates:
        slice_ = valid[valid["date"] == d]
        rows.append({
            "date": d,
            "stock": float(slice_["quantity"].sum()),
            "avg_rate": _wavg(slice_),
            "importers": int(slice_["importer"].nunique()),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------ data quality
def quality_report(df: pd.DataFrame, quality: pd.DataFrame) -> dict:
    valid = analysis_rows(df)
    incomplete = int((~df["is_complete_row"] & df["date"].notna()).sum())
    no_rate = int((valid["has_stock"] & (valid["sale_rate"] <= 0)).sum())
    missing_origin = int(valid["origin"].eq("").sum())

    similar: list[tuple[str, str, float]] = []
    names = sorted({n for n in valid["importer"].unique() if n})
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
            if ratio >= 0.86:
                similar.append((a, b, ratio))

    return {
        "rows_total": int(df["date"].notna().sum()),
        "rows_used": int(len(valid)),
        "incomplete": incomplete,
        "no_rate": no_rate,
        "missing_origin": missing_origin,
        "similar_names": similar,
        "quality": quality,
    }


# ---------------------------------------------------------------- formatting
def fmt_int(x: float | int | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:,.0f}"


def fmt_rate(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:,.0f}"


def fmt_rate2(x: float | None) -> str:
    """Rate with up to 2 decimals, like the reference's nf2 formatter."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    text = f"{x:,.2f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def fmt_pct(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x * 100:,.1f}%"


def fmt_date(d: pd.Timestamp | None) -> str:
    if d is None or pd.isna(d):
        return "—"
    return pd.Timestamp(d).strftime("%d %b %Y")
