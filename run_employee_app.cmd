@echo off
REM ====================================================
REM Launcher for the Employee Skill Tracker
REM Employees can view and update their own skills only.
REM No access to other people's data.
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
echo Launching Employee Skill Tracker (port 8501)...
echo (If the browser does not open automatically, open: http://localhost:8501)
python -m streamlit run scripts\app_employee.py --server.port 8501

echo.
pause
