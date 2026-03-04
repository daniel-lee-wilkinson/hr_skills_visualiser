@echo off
REM ====================================================
REM install.cmd  —  One-time setup for Skill Tracker
REM Run this once on any machine before using the app.
REM ====================================================

cd /d "%~dp0"
echo.
echo ============================================================
echo  Skill Tracker — Setup
echo ============================================================

REM ── 1. Python virtual environment ──────────────────────────
echo.
echo [1/4] Setting up Python virtual environment...
if not exist ".venv" (
    python -m venv .venv
    echo      Created .venv
) else (
    echo      .venv already exists, skipping.
)
call ".venv\Scripts\activate"

REM ── 2. Install requirements ─────────────────────────────────
echo.
echo [2/4] Installing Python packages...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo      Done.

REM ── 3. Local .env — always use demo DB for development ──────
echo.
echo [3/4] Writing local .env (dev)...
(
    echo # Local development — uses demo database.
    echo # SKILLS_ENV_PATH is written below if you choose shared DB setup.
    echo SKILLS_DB=skills_demo.db
) > .env
echo      .env written.

REM ── 4. Shared / production database setup ───────────────────
echo.
echo [4/4] Production database setup
echo.
echo Do you want to configure a shared production database now?
echo (Choose N if you are installing on a dev machine or if the
echo  shared drive is not available yet.)
echo.
set /p SETUP_PROD="Configure shared DB? [Y/N]: "
if /i not "%SETUP_PROD%"=="Y" goto :skip_prod

REM Ask for shared folder path
echo.
echo Enter the full path to the shared folder where the database
echo should be stored.  Press ENTER to accept the default.
echo.
set "DEFAULT_SHARE=C:\Skills_Tracker"
set /p SHARE_DIR="Shared folder path [%DEFAULT_SHARE%]: "
if "%SHARE_DIR%"=="" set "SHARE_DIR=%DEFAULT_SHARE%"

REM Create the shared folder if it does not exist
if not exist "%SHARE_DIR%" (
    mkdir "%SHARE_DIR%"
    echo Created folder: %SHARE_DIR%
)

REM Ask for DB filename
set "DEFAULT_DB=prod_skills.db"
set /p DB_NAME="Database filename [%DEFAULT_DB%]: "
if "%DB_NAME%"=="" set "DB_NAME=%DEFAULT_DB%"

set "DB_FULL=%SHARE_DIR%\%DB_NAME%"

REM Write the shared .env (contains the absolute DB path for production)
(
    echo # Production override — loaded automatically via SKILLS_ENV_PATH.
    echo # Path must be absolute so it works from any working directory.
    echo SKILLS_DB=%DB_FULL%
) > "%SHARE_DIR%\.env"

REM Point the local .env at the shared .env via SKILLS_ENV_PATH
echo SKILLS_ENV_PATH=%SHARE_DIR%\.env >> .env
echo.
echo Written: %SHARE_DIR%\.env

REM Initialise the DB schema (idempotent — safe to run on an existing DB)
echo.
echo Initialising database schema at: %DB_FULL%
python -c "import sqlite3, sys; sys.path.insert(0,'%~dp0'); from scripts.db import create_schema; conn=sqlite3.connect(r'%DB_FULL%'); create_schema(conn); conn.close(); print('Schema ready.')"

echo.
echo ── Production setup complete ──────────────────────────────
echo    Shared folder : %SHARE_DIR%
echo    Database file : %DB_FULL%
echo    Config file   : %SHARE_DIR%\.env
echo.
echo Any machine that has %SHARE_DIR% accessible will
echo automatically use this database when running the app.

goto :done

:skip_prod
echo.
echo Skipped — app will use skills_demo.db (local demo data).
echo Run install.cmd again whenever the shared drive is ready.

:done
echo.
echo ============================================================
echo  Setup complete.
echo  - Employee app : run_employee_app.cmd
echo  - Management   : run_management_app.cmd
echo ============================================================
echo.
pause
