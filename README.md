# Coal Market Dashboard — Streamlit edition

A live Streamlit dashboard for the **Master Database** tab of your Google Sheet.
The look is copied 1:1 from <https://coal-dashboard.vercel.app/> — same palette,
gradient header, pill badges, filter bar, two KPI cards and the same 2×2 chart grid.

```
coal-streamlit/
├─ app.py                 single-page dashboard (header, filters, KPIs, charts)
├─ config.py              sheet id, importer aliases, completeness rule
├─ core/
│  ├─ source.py           live Google Sheet download + offline snapshot fallback
│  ├─ transform.py        cleaning, weighted rates, snapshot logic, aggregations
│  ├─ charts.py           the four Plotly charts, styled like the reference
│  ├─ theme.py            design system + HTML components (header, KPIs, footer)
│  ├─ filters.py          top filter bar (5 selects + reset)
│  └─ sheet_write.py      optional upload/write-back via a service account
├─ views/admin.py         upload, data health, connection (bottom panel)
├─ data/master_database_snapshot.csv   offline fallback copy of your data
├─ .streamlit/config.toml
├─ .streamlit/secrets.toml.example
├─ requirements.txt
├─ run.bat                start locally
├─ public_link.bat        temporary public HTTPS link via Cloudflare
└─ README.md
```

---

## 1. Run it

Double-click **`run.bat`**. First run creates `.venv`, installs the packages and
opens <http://localhost:8501>.

Manual:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Your `python` command is the Microsoft Store alias, so `run.bat` looks for the real
interpreter in `%LOCALAPPDATA%\Programs\Python\Python312\`.

---

## 2. Live connection

The workbook is shared as "anyone with the link", so the app downloads it directly:

```
https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=xlsx
```

* Each page load reads the sheet (cached **2 minutes**), and the page re-renders
  itself every **2 minutes** so new rows appear without anyone clicking.
* **Refresh now** in the bottom *Connection* tab clears the cache immediately.
* If Google is unreachable, the bundled snapshot is shown and the header pill says
  **Snapshot** instead of **Live**.

**Recommended one-time upgrade:** open the workbook in Google Sheets →
**File → Save as Google Sheets**, put the new file id in `SHEET_ID` and the tab's
`gid` in `MASTER_GID` (`config.py`). Reading by gid is faster and is required for
in-app uploads. Keep using the same file afterwards — a new Drive file gets a new
id and the dashboard would keep reading the old one.

---

## 3. Public link from anywhere

### 3a. Temporary link from this PC (1 minute, no accounts)

Double-click **`public_link.bat`**. It starts the dashboard, downloads the Cloudflare
tunnel client once, and prints a link like:

```
https://something-random.trycloudflare.com
```

That link works worldwide over HTTPS. Caveats: this PC must stay on, the address
changes each time you restart the script, and it is not meant for permanent use.

### 3b. Permanent public URL (Streamlit Community Cloud, free)

1. Create a GitHub account, install **GitHub Desktop**, and sign in.
2. GitHub Desktop → **File → Add local repository** → choose this `coal-streamlit`
   folder → it offers to **create a repository** → choose **Private**.
3. Click **Publish repository** (this puts the code on GitHub; `.venv` and secrets
   are ignored).
4. <https://share.streamlit.io> → **New app** → pick the repo → branch `main` →
   main file `app.py` → **Deploy**.
5. Share the `*.streamlit.app` URL. It stays up when your PC is off; the free tier
   sleeps after inactivity and wakes in ~30 seconds.

No password is set, so the link is open to anyone who has it. To restrict it, add
`[app] password = "..."` under **Advanced settings → Secrets**. The public app is
read-only unless you also connect the service account for uploads.

### 3c. Sharing with the team / uploads

Already works, no credentials needed. Add the new week's rows in the Google Sheet;
the dashboard picks it up within ~2 minutes (or immediately with **Refresh now**).

### 3d. Upload inside the dashboard

Open **Weekly upload & data health** at the bottom of the page → **Upload a week**.
The file is validated, de-duplicated and previewed before anything is written.
This needs a Google **service account** because the API cannot write anonymously:

1. Google Cloud Console → new project → enable **Google Sheets API** and
   **Google Drive API**.
2. Create a **service account** → **Keys → Add key → JSON** → download.
3. Convert the workbook to a native Google Sheet (**File → Save as Google Sheets**).
4. Share that Sheet with the service-account `client_email` as **Editor**.
5. Put the new file id in `config.py`.
6. Paste the JSON into `.streamlit/secrets.toml` under `[gcp_service_account]`.
7. Open the Connection tab → **Test write access**.

Uploads write columns `A:M` plus the workbook's own `N`/`O` formulas into the first
empty row. Nothing above is touched.

**Upload rules:** same headers as the Master Database tab; date as a real date,
`2026-10-25`, `25/10/2026` or an Excel serial; rows without Date, Location or
Importer are rejected; re-uploaded rows are skipped by default. A template is
available in the upload panel.

---

## 4. What is on the page

| Area | Content |
|---|---|
| Header | gradient banner, Live/Snapshot pill, report date, last sync time |
| Filter bar | **Date, Location, Importer, Origin, Remarks** + Reset filters |
| KPI cards | Total stock (MT) · quantity-weighted avg sale rate (BDT/MT) |
| Charts | Location-wise stock · Origin avg stock + avg sale rate · Importer avg sale rate · Importer-wise stock |
| Footer | definitions, plus the data panel |

* Filters are single-select with an **"All …"** default, exactly like the reference.
  Type in a select to search.
* Date defaults to the **latest complete week**; other dates (including an
  in-progress week) are marked in the dropdown.
* Charts are Plotly: hover for values, drag to zoom, double-click to reset.
* **Weekly upload & data health** sits below the footer in a collapsed panel.

---

## 5. Rules that keep the numbers honest

1. **Stock is never summed across weeks.** One date = one snapshot.
2. **A half-entered week is not the default.** A date becomes the default when it has
   at least 60% of the biggest week's usable rows (`COMPLETENESS_RATIO`). Your
   `2026-10-18` block has 19 filled rows out of 126 date-stamped rows, so the page
   opens on `2026-10-11` — the same data your Top Sheet reports. You can still pick
   `18 Oct 2026 · in progress` from the date filter.
3. **Rows with no Location or Importer are ignored** (the 107 rows on `2026-10-18`
   that only carry a date). They are counted in **Data health**.
4. **Sale-rate averages are quantity-weighted and ignore blank/zero rates**, matching
   your Report sheet: `Σ(qty × rate) / Σ(qty)`.
5. **Avg stock per entry** = total stock ÷ entries with stock > 0 — the reference
   dashboard's definition, shown in the Origin chart tooltip.

### Data notes found in the current sheet

* `2026-10-11`: 84 usable rows, 487,100 MT — matches the Top Sheet.
* `2026-10-18`: 126 stamped rows, only 19 filled and all at Noapara → in progress.
* Near-duplicate importer names: `Sahara` / `Shara`, `Soinik Enterprise` /
  `Soinik Traders`, `Sheikh Brothers` / `Sheikh Bhorthers`. Only obvious spelling
  variants are merged (`config.IMPORTER_ALIASES`). `Shara` and the two Soinik names
  are deliberately kept separate — confirm with the team, then add them to the
  alias map if they are the same company.
* The workbook's `N`/`O` columns are formulas; the dashboard derives "upcoming"
  from Status + Remarks and never depends on those formulas being filled.

---

## 6. Customising

| Change | Where |
|---|---|
| Sheet / tab / gid | `config.py` → `SHEET_ID`, `MASTER_SHEET_NAME`, `MASTER_GID` |
| Merge importer names | `config.py` → `IMPORTER_ALIASES` |
| When a week becomes the default | `config.py` → `COMPLETENESS_RATIO` |
| Open on the newest date even if partial | `config.py` → `DEFAULT_TO_LATEST_DATE = True` |
| Cache duration | `config.py` → `CACHE_TTL_SECONDS` |
| Colours / spacing / fonts | `core/theme.py` → `CSS` |
| Chart colours | `core/charts.py` (top constants) |
| Password | `.streamlit/secrets.toml` → `[app] password` |

New locations, origins and importers need no code change — they appear in the
filters on the next refresh.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Header shows **Snapshot** | Google was unreachable or the share setting changed. Check the link in a browser, then **Refresh now**. |
| Old week shows by default | A newer week has not reached the 60% completeness bar, or the 2-minute cache has not expired. |
| Upload says "cannot write … .xlsx" | Convert the workbook to a native Google Sheet and update `SHEET_ID`. |
| Upload says "no write permission" | Share the Sheet with the service-account email as **Editor**. |
| Login loop | The password in secrets does not match; remove `[app] password` to test open access. |
| Charts look empty | No rows match the filters — press **Reset filters**. |

---

The sheet stays the single source of truth; the dashboard only reads and (optionally)
appends to it.
