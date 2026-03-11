"""
app_common.py – shared setup, DB connection, and cached data loaders.

Both app_employee.py and app_management.py import from here so that
environment / database configuration lives in exactly one place.
"""
import os
import sys
import sqlite3
from pathlib import Path

# Ensure the project root is on sys.path whether the app is launched from
# the root or from inside scripts/.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from scripts.db import (
    upsert_person as _upsert_person,
    get_existing_skills as _get_existing_skills,
    get_existing_applications as _get_existing_applications,
    upsert_application as _upsert_application,
    upsert_skill_entry as _upsert_skill_entry,
    delete_skill as _delete_skill,
)

# ─────────────────────────────────────────────
# Environment / DB path resolution
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")          # local dev config (skills_demo.db by default)

# Optional second .env for production — path comes from SKILLS_ENV_PATH in the
# local .env (written by install.cmd). Nothing is hardcoded here, so cloning
# this repo reveals no private paths.
_override_env = os.getenv("SKILLS_ENV_PATH", "")
if _override_env and Path(_override_env).exists():
    load_dotenv(_override_env, override=True)

DB_FILE = os.getenv("SKILLS_DB", "skills_demo.db")
DB_PATH = BASE_DIR / DB_FILE if not Path(DB_FILE).is_absolute() else Path(DB_FILE)


# ─────────────────────────────────────────────
# Shared DB connection  (one per process)
# ─────────────────────────────────────────────
@st.cache_resource
def get_connection():
    """Return a single shared SQLite connection for this Streamlit process.
    WAL mode allows concurrent reads without locking out writers.
    """
    _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA synchronous=NORMAL")
    return _conn


# ─────────────────────────────────────────────
# Thin DB wrappers  (accept conn so apps can pass their own)
# ─────────────────────────────────────────────
def upsert_person(conn, email, first_name="", last_name=""):
    _upsert_person(conn, conn.cursor(), email, first_name, last_name)


def get_existing_skills(conn, term=""):
    return _get_existing_skills(conn.cursor(), term)


def get_existing_applications(conn, term=""):
    return _get_existing_applications(conn.cursor(), term)


def upsert_application(conn, name):
    return _upsert_application(conn, conn.cursor(), name)


def upsert_skill_entry(conn, email, skill, field, theo, prac, interest, field_proficiency):
    _upsert_skill_entry(conn, conn.cursor(), email, skill, field, theo, prac, interest, field_proficiency)
    st.cache_data.clear()   # invalidate all cached query results


def delete_skill(conn, email, skill=None):
    _delete_skill(conn, conn.cursor(), email, skill)
    st.cache_data.clear()   # invalidate all cached query results


# ─────────────────────────────────────────────
# Cached data loaders  (used by management app)
# ─────────────────────────────────────────────
@st.cache_data
def load_analytics_data(_conn):
    """All SkillEntry rows joined with Person name fields — used by the management analytics tab."""
    return pd.read_sql_query(
        """
        SELECT se.email, se.skill_name AS skill, se.field_of_use,
               se.theoretical_level, se.practical_level, se.interest,
               se.field_proficiency
        FROM SkillEntry se
        ORDER BY se.email, se.skill_name, se.field_of_use
        """,
        _conn,
    )


@st.cache_data
def load_individual_data(_conn):
    """Per-person skill entries joined with Person name fields."""
    return pd.read_sql_query(
        """
        SELECT p.first_name, p.last_name, se.email,
               se.skill_name AS skill, se.field_of_use,
               se.theoretical_level, se.practical_level,
               se.interest, se.field_proficiency
        FROM SkillEntry se
        LEFT JOIN Person p ON se.email = p.email
        ORDER BY se.email, se.skill_name, se.field_of_use
        """,
        _conn,
    )


@st.cache_data
def load_applications(_conn):
    return [r[0] for r in _conn.execute("SELECT name FROM Application ORDER BY name").fetchall()]
