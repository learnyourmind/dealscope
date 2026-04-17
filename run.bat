@echo off
echo.
echo   DealScope -- Real Estate Investment Analyzer
echo   =============================================
echo   Zero API keys required
echo.
echo   Installing dependencies...
pip install flask flask-cors requests --quiet
echo.
echo   Starting server...
echo.
echo   Open your browser at: http://localhost:5000
echo.
python app.py
pause
