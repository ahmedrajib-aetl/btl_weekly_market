"""Data panel: upload a week, data health, connection - shown below the dashboard."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

import config
from core import sheet_write, source, transform


def render(ctx: dict, meta: dict) -> None:
    tabs = st.tabs(["Upload a week", "Data health", "Connection"])
    with tabs[0]:
        _upload_block(ctx)
    with tabs[1]:
        _quality_block(ctx)
    with tabs[2]:
        _connection_block(meta)


# ------------------------------------------------------------------ upload
def _upload_block(ctx: dict) -> None:
    if st.session_state.get("_upload_ok"):
        message = st.session_state.pop("_upload_ok")
        st.success(message)
        st.session_state.pop("_admin_open", None)

    configured = sheet_write.is_configured()
    st.caption(
        "Every upload is validated first: required columns, dates, numbers and "
        "duplicates. Rows are appended to the Master Database tab; nothing is overwritten."
    )

    template_cols = config.MASTER_COLUMNS[:13]
    example = {
        "Date": "2026-10-25",
        "Location": "Noapara",
        "Importer": "Example Importer",
        "Origin": "South Africa",
        "Coal Grade / Cal (kcal)": "5500",
        "Mine": "",
        "Quantity (MT)": "5000",
        "Bulk Purchase Rate (BDT/MT)": "",
        "Sale / Retail Rate (BDT/MT)": "20000",
        "Status": "Dumped",
        "Remarks": "New arrival",
        "Vessel Name": "",
        "Vessel Qty (MT)": "",
    }
    template = pd.DataFrame([example], columns=template_cols)
    st.download_button(
        "Download upload template (CSV)",
        data=template.to_csv(index=False).encode("utf-8-sig"),
        file_name="master_database_upload_template.csv",
        mime="text/csv",
    )

    upload = st.file_uploader(
        "This week's rows", type=["csv", "xlsx"],
        help="Use the same column headers as the Master Database tab.",
    )
    if not upload:
        if not configured:
            st.info(
                "Reading is live already. To let the team upload from here, connect a "
                "Google service account - see the Connection tab.",
                icon="🔐",
            )
        return

    try:
        if upload.name.lower().endswith((".xlsx", ".xlsm")):
            raw_up = pd.read_excel(io.BytesIO(upload.getvalue()), sheet_name=0)
        else:
            raw_up = pd.read_csv(io.BytesIO(upload.getvalue()), encoding="utf-8-sig")
    except Exception as exc:
        st.error(f"Could not read that file: {exc}")
        return

    try:
        up = transform.prepare(raw_up, apply_aliases=False)
    except Exception as exc:
        st.error(str(exc))
        return

    valid_up = up[up["is_complete_row"]].copy()
    rejected = up[~up["is_complete_row"]]

    st.markdown(
        f'<span class="pill" style="background:#0f1a2b;border-color:#26334a">READY '
        f"<b>{len(valid_up)}</b></span> "
        f'<span class="pill" style="background:#0f1a2b;border-color:#26334a">REJECTED '
        f"<b>{len(rejected)}</b></span>",
        unsafe_allow_html=True,
    )

    if len(rejected):
        with st.expander(f"Why {len(rejected)} rows were rejected"):
            bad = rejected[["date", "location", "importer", "origin", "quantity"]].copy()
            bad["date"] = bad["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(bad.head(50), hide_index=True, width="stretch")
            st.caption("Rows need a valid Date, Location and Importer.")

    if valid_up.empty:
        st.error("No valid rows to upload.")
        return

    existing = {sheet_write.key_for_row(r) for _, r in ctx["all_valid"].iterrows()}
    dup_mask = valid_up.apply(lambda r: sheet_write.key_for_row(r) in existing, axis=1)
    duplicate_count = int(dup_mask.sum())
    skip_duplicates = True
    if duplicate_count:
        st.warning(
            f"{duplicate_count} of these rows already exist (same date, location, "
            "importer, origin, quantity and rate)."
        )
        skip_duplicates = st.checkbox("Skip rows that already exist", value=True)

    to_write = valid_up[~dup_mask] if (duplicate_count and skip_duplicates) else valid_up

    preview = to_write.copy()
    preview["date"] = preview["date"].dt.strftime("%Y-%m-%d")
    preview = preview[[
        "date", "location", "importer", "origin", "quantity", "sale_rate",
        "remarks", "status",
    ]].rename(columns={
        "date": "Date", "location": "Location", "importer": "Importer",
        "origin": "Origin", "quantity": "Qty (MT)",
        "sale_rate": f"Sale rate ({config.CURRENCY}/MT)",
        "remarks": "Remarks", "status": "Status",
    })
    st.caption(f"Preview · {len(preview)} rows will be appended")
    st.dataframe(preview, hide_index=True, width="stretch", height=260)

    if to_write["date"].nunique() == 1:
        d0 = to_write["date"].iloc[0]
        if d0 in ctx["quality"].index:
            st.warning(
                f"{transform.fmt_date(d0)} already exists in the Master Database. "
                "Uploading will add a second block for the same date."
            )

    if not configured:
        st.info(
            "Upload is preview-only until a Google service account is connected. "
            "You can still download the cleaned rows and paste them into the sheet.",
            icon="🔐",
        )
        st.download_button(
            "Download validated rows (CSV)",
            data=to_write.drop(columns=[
                "weighted_value", "weight", "is_complete_row", "upcoming",
                "has_stock", "rate_ok",
            ]).to_csv(index=False).encode("utf-8-sig"),
            file_name="validated_rows.csv",
            mime="text/csv",
        )
        return

    confirmed = st.checkbox(
        "I checked these rows and want to append them to the Master Database",
        key="confirm_upload",
    )
    if st.button("Append to Google Sheet", type="primary", disabled=not confirmed):
        with st.spinner("Writing to Google Sheets…"):
            ok, message = sheet_write.append_rows(to_write)
        if ok:
            st.session_state["_upload_ok"] = message
            st.session_state["_admin_open"] = True
            source.clear_cache()
            st.rerun()
        else:
            st.error(message)


# ------------------------------------------------------------- data health
def _quality_block(ctx: dict) -> None:
    quality = ctx["quality"].copy()
    report = transform.quality_report(ctx["raw"], ctx["quality"])

    table = quality.reset_index().rename(columns={
        "date": "Report date",
        "rows_total": "Rows stamped",
        "rows_valid": "Rows usable",
        "importers": "Importers",
        "stock": "Stock (MT)",
        "complete": "Complete week",
    })
    table["Report date"] = pd.to_datetime(table["Report date"]).dt.strftime("%d %b %Y")
    st.dataframe(
        table[["Report date", "Rows stamped", "Rows usable", "Importers",
               "Stock (MT)", "Complete week"]],
        hide_index=True,
        width="stretch",
        column_config={
            "Rows stamped": st.column_config.NumberColumn(format="%d"),
            "Rows usable": st.column_config.NumberColumn(format="%d"),
            "Importers": st.column_config.NumberColumn(format="%d"),
            "Stock (MT)": st.column_config.NumberColumn(format="%,.0f"),
            "Complete week": st.column_config.CheckboxColumn(),
        },
    )
    st.caption(
        f"A week counts as complete once it has at least "
        f"{int(quality['threshold'].iloc[0])} usable rows (60% of the biggest week). "
        "Partly entered weeks are marked in progress in the date filter."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows skipped (no location/importer)", f"{report['incomplete']:,}")
    c2.metric("Stock rows without a sale rate", f"{report['no_rate']:,}")
    c3.metric("Rows with no origin", f"{report['missing_origin']:,}")

    if report["similar_names"]:
        st.caption(
            "Similarly spelled importer names - confirm before merging them in "
            "IMPORTER_ALIASES inside config.py."
        )
        for a, b, ratio in report["similar_names"][:8]:
            st.markdown(f"- **{a}** · {b} · {ratio * 100:.0f}% similar")


# ------------------------------------------------------------- connection
def _connection_block(meta: dict) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Refresh now", type="primary", width="stretch"):
            source.clear_cache()
            st.rerun()
    with c2:
        if st.button("Test write access", width="stretch"):
            ok, message = sheet_write.test_connection()
            (st.success if ok else st.warning)(message)
    with c3:
        st.caption(f"Synced {source.age_label(meta['fetched_at'])}")

    used_id = meta.get("sheet_id") or config.SHEET_ID
    if used_id != config.SHEET_ID:
        st.warning(
            "The primary workbook is not publicly readable, so the dashboard is using "
            f"the fallback file `{used_id}`. Set the new file to "
            '"Anyone with the link → Viewer" to switch to it.'
        )

    st.markdown(
        f"**Source** · {meta['source']}  \n"
        f"**Sheet id** · `{used_id}`  \n"
        f"**Tab** · `{config.MASTER_SHEET_NAME}`  \n"
        f"**Auto refresh** · every {config.CACHE_TTL_SECONDS // 60} minutes"
    )
    st.markdown(
        f"[Open the workbook](https://docs.google.com/spreadsheets/d/{used_id}/edit)"
    )

    with st.expander("Connect uploads (one-time setup)"):
        st.markdown(
            "Reading is live with no setup. Writing needs a Google service account:\n"
            "1. Google Cloud Console → create a project → enable **Google Sheets API** "
            "and **Google Drive API**.\n"
            "2. Create a **service account**, add a JSON key, download it.\n"
            "3. Open the workbook in Google Sheets → **File → Save as Google Sheets** "
            "(the API cannot write to an .xlsx).\n"
            "4. Share the new Sheet with the service-account email as **Editor**.\n"
            "5. Put the new file id in `config.py` and the JSON in "
            "`.streamlit/secrets.toml` under `[gcp_service_account]`."
        )
        email = sheet_write.service_account_email()
        if email:
            st.code(email, language="text")
        st.code(
            '[gcp_service_account]\n'
            'type = "service_account"\n'
            'project_id = "..."\n'
            'private_key_id = "..."\n'
            'private_key = "-----BEGIN PRIVATE KEY-----\\n..."\n'
            'client_email = "..."\n'
            'client_id = "..."\n'
            'auth_uri = "https://accounts.google.com/o/oauth2/auth"\n'
            'token_uri = "https://oauth2.googleapis.com/token"\n'
            'auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"\n'
            'client_x509_cert_url = "..."\n'
            '\n[app]\npassword = "choose-a-team-password"',
            language="toml",
        )
