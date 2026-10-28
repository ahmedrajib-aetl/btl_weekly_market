"""Central configuration for the coal market dashboard.

Everything a normal user might want to change lives here.
"""

# ---------------------------------------------------------------- data source
# Primary workbook. NOTE: this file must be shared as "Anyone with the link ->
# Viewer" for the dashboard to read it. It is tried first; if Google refuses it
# (401/403), the app falls back to the ids below so the dashboard keeps working.
SHEET_ID = "1EQBuUlDPQS3fPP5yOTfWe-R9JPml1kT0"

# Fallbacks, in order. The second id is the file the dashboard used before and
# already contains the same daily data (through 2026-10-28).
SHEET_FALLBACKS = [
    "1RbZLnMtinR6H7SD_mZmDX-KD0Sy1m1cA",
]

# Tab that holds the raw weekly rows.
MASTER_SHEET_NAME = "Master Database"

# If you convert the workbook to a native Google Sheet, put the tab's gid here
# (the number after #gid= in the URL). Leave as None to read the .xlsx export.
# Reading by gid is faster and works even when the file has many tabs.
MASTER_GID = None

# Read live from Google every N seconds. The manual "Refresh now" button always
# bypasses the cache.
CACHE_TTL_SECONDS = 120
REQUEST_TIMEOUT_SECONDS = 30

# The page re-renders itself on this interval, so new rows appear without a click.
AUTO_REFRESH_SECONDS = 120

# Used when Google cannot be reached (offline preview / demo).
LOCAL_SNAPSHOT = "data/master_database_snapshot.csv"

# ------------------------------------------------------------- data behaviour
# A report date is treated as "complete" when it has at least this share of the
# biggest week's row count. This stops a half-entered next week from becoming
# the default view.
COMPLETENESS_RATIO = 0.6
MIN_ROWS_FOR_COMPLETE = 5

# What the page opens on:
#   True  = newest date in the sheet (daily data - what this dashboard now uses).
#   False = newest *complete* week (only for the old weekly layout).
DEFAULT_TO_LATEST_DATE = True

# How many importers to draw before grouping the tail into "Other".
TOP_N_IMPORTERS = 18

# Friendly merge of obvious spelling variants. Keys are what appears in the
# sheet, values are the canonical name. Set to {} to show raw sheet values.
# Anything not listed here is left untouched on purpose - the dashboard never
# guesses that two different company names are the same company.
IMPORTER_ALIASES = {
    "Sahara Entr": "Sahara",
    "Mosharrof Entr": "Mosharrof",
    "Mostofa Zamana": "Mostofa Zaman",
    "Sheikh Bhorthers": "Sheikh Brothers",
    "M/S Soinik Enterprise": "Soinik Enterprise",
}

# Names that look similar but are kept separate. Surfaced in Data & Refresh so
# the team can confirm before adding them to IMPORTER_ALIASES.

# --------------------------------------------------------------------- labels
APP_TITLE = "Coal Market Dashboard"
APP_SUBTITLE = "Bangladesh import market · weekly snapshot"
CURRENCY = "BDT"
UNIT = "MT"

# Column letters in the Master Database (used when appending rows).
MASTER_COLUMNS = [
    "Date", "Location", "Importer", "Origin", "Coal Grade / Cal (kcal)",
    "Mine", "Quantity (MT)", "Bulk Purchase Rate (BDT/MT)",
    "Sale / Retail Rate (BDT/MT)", "Status", "Remarks", "Vessel Name",
    "Vessel Qty (MT)", "Upcoming # (auto)", "Is Upcoming (auto)",
]

# Excel formulas mirrored for rows uploaded through the dashboard, so the
# workbook's own Top Sheet keeps working. {r} is replaced by the row number.
UPCOMING_NO_FORMULA = (
    "=IF(AND(ISNUMBER($A{r}),$A{r}='Top Sheet'!$B$3,$O{r}=1),"
    'MAX($N$1:$N{prev})+1,"")'
)
IS_UPCOMING_FORMULA = (
    '=IF(OR($J{r}="In-transit",$J{r}="Expected",$J{r}="Delayed",'
    '$K{r}="Vessel up coming"),1,0)'
)
