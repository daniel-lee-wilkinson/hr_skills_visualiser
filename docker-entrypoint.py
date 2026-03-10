"""
docker-entrypoint.py

Initialises the SQLite database on first launch (if the file does not yet
exist), then exec's Streamlit so it becomes PID 1 and receives signals
correctly.

Environment variables (all set in docker-compose.yml):
    SKILLS_DB       Absolute path to the database file  (default: /data/skills.db)
    APP_SCRIPT      Streamlit script to run             (default: scripts/app_employee.py)
    PORT            Port Streamlit listens on           (default: 8501)
    SEED_DEMO_DATA  Set to "true" to populate a fresh DB with synthetic data
"""

import os
import sys
import pathlib
import sqlite3

sys.path.insert(0, "/app")

DB_PATH = pathlib.Path(os.environ.get("SKILLS_DB", "/data/skills.db"))
SEED_DEMO = os.environ.get("SEED_DEMO_DATA", "false").lower() == "true"
APP_SCRIPT = os.environ.get("APP_SCRIPT", "scripts/app_employee.py")
PORT = os.environ.get("PORT", "8501")

# ── Initialise database on first run ─────────────────────────────────────────
if not DB_PATH.exists():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"[entrypoint] Database not found at {DB_PATH} — initialising...")

    if SEED_DEMO:
        from scripts.make_demo_db import seed_demo_db
        seed_demo_db(DB_PATH)
        print("[entrypoint] Demo database created with synthetic data.")
    else:
        from scripts.db import create_schema
        conn = sqlite3.connect(str(DB_PATH))
        create_schema(conn)
        conn.close()
        print("[entrypoint] Empty production database initialised.")
else:
    print(f"[entrypoint] Database found at {DB_PATH}.")

# ── Start Streamlit (replaces this process so signals work correctly) ─────────
print(f"[entrypoint] Starting: streamlit run {APP_SCRIPT} --server.port {PORT}")
os.execvp(
    "streamlit",
    [
        "streamlit", "run", APP_SCRIPT,
        "--server.port", PORT,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
    ],
)
