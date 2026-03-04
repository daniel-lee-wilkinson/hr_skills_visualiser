@echo off
REM ====================================================
REM Launcher for the Management Skill Tracker
REM Contains personal data — restrict to authorised
REM HR / management personnel only.
REM ====================================================

cd /d "%~dp0"
echo.
echo Current directory: %cd%

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo.
echo Activating virtual environment...
call ".venv\Scripts\activate"

echo.
where python
python --version

echo.
echo Installing required Python packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Launching Management Skill Tracker (port 8502)...
echo (If the browser does not open automatically, open: http://localhost:8502)
python -m streamlit run scripts\app_management.py --server.port 8502

echo.
pause
