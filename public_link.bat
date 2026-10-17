@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Run run.bat once first to install the app.
    pause
    exit /b 1
)

if not exist "tools\cloudflared.exe" (
    echo Downloading the Cloudflare tunnel client ^(~55 MB, one time^)...
    if not exist tools mkdir tools
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'tools\cloudflared.exe' -UseBasicParsing"
    if errorlevel 1 (
        echo Download failed. Check your internet connection and run again.
        pause
        exit /b 1
    )
)

echo Starting the dashboard...
start "Coal Dashboard" ".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true
timeout /t 7 /nobreak >nul

echo.
echo ============================================================
echo  A public https address will appear below.
echo  Copy it and share it. Keep THIS window open while people use it.
echo  The address changes every time you restart this script.
echo ============================================================
echo.
tools\cloudflared.exe tunnel --url http://localhost:8501 --no-autoupdate
pause
