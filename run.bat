@echo off
cd /d "%~dp0"
echo.
echo   DealScope -- first-pass rental property analysis
echo   ================================================
echo.
if not exist .venv (
    echo   Creating virtual environment...
    python -m venv .venv
)
echo   Installing dependencies from requirements.txt...
.venv\Scripts\pip install --quiet -r requirements.txt
echo.
echo   Open your browser at: http://localhost:5000
echo.
.venv\Scripts\python app.py
pause
