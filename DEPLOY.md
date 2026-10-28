# Deploy in the browser (no Git needed)

1. Open <https://github.com/new>
   - Repository name: `coal-dashboard`
   - Visibility: **Private**
   - Do **not** add a README (this folder already has one)
   - **Create repository**

2. On the empty repository page click **uploading an existing file**
   (or **Add file → Upload files**).

3. In File Explorer open:
   `C:\Users\Laptop Click\OneDrive\Documents\Default Project\coal-dashboard-upload`
   Select **everything inside** it (Ctrl+A) and drag it into the browser.
   Upload the **contents**, not the folder itself.

4. Check the file list shows:
   - `app.py`, `config.py`, `requirements.txt`
   - `core/` and `views/` folders
   - `.streamlit/config.toml`
   - `data/master_database_snapshot.csv`

5. Commit message: `Initial commit` → **Commit changes**.

6. Open <https://share.streamlit.io> → **Create app** →
   **Deploy a public app from GitHub**
   - Repository: `your-username/coal-dashboard`
   - Branch: `main`
   - Main file path: `app.py`
   - Optional: **Advanced settings → Secrets**
     ```
     [app]
     password = "your-team-password"
     ```
   - **Deploy**.

7. First build takes 2–4 minutes. The permanent URL appears at the top
   (e.g. `https://coal-dashboard-btl.streamlit.app`).

## If the repository is not in the dropdown

Click **Configure GitHub access** → grant Streamlit access → choose
**Only select repositories** → tick `coal-dashboard` → save → refresh.

## If `.streamlit/config.toml` is missing after the upload

GitHub's uploader sometimes skips dot-folders. Recreate it:

**Add file → Create new file** → name: `.streamlit/config.toml` → paste:

```toml
[theme]
base = "dark"
primaryColor = "#14b8a6"
backgroundColor = "#0b1220"
secondaryBackgroundColor = "#131c2e"
textColor = "#e8eef8"

[server]
headless = true

[browser]
gatherUsageStats = false

[client]
toolbarMode = "minimal"
```

→ **Commit changes**.

## Updating later

- Data: nothing to do — the dashboard re-reads the Google Sheet every 2 minutes.
- Code: edit the file on GitHub (pencil icon) → commit → Streamlit redeploys itself.
