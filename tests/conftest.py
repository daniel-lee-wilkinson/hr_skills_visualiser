"""
conftest.py — Shared pytest fixtures for the Skill Tracker test suite.

Two fixture tiers:
  blank_db       — empty schema, no data.  For pure unit tests of db.py helpers.
  seeded_db_path — demo data (same as make_demo_db), env var pointing at temp file.
                   For AppTest integration tests.
"""

import os
import sqlite3
import pathlib

import pytest
import streamlit as st

from scripts.db import create_schema
from scripts.make_demo_db import seed_demo_db


# ─────────────────────────────────────────────────────────────
# Unit-test fixture: bare schema, no data
# ─────────────────────────────────────────────────────────────

@pytest.fixture()
def blank_db(tmp_path: pathlib.Path):
    """Yields (conn, cur) pointing at a fresh, schema-only SQLite file.

    The connection is closed automatically after the test.
    """
    db_path = tmp_path / "test_blank.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    cur = conn.cursor()
    yield conn, cur
    conn.close()


# ─────────────────────────────────────────────────────────────
# Integration-test fixtures: seeded DB + env-var redirection
# ─────────────────────────────────────────────────────────────

@pytest.fixture()
def seeded_db_path(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Seed a temp DB, redirect SKILLS_DB env var to it, yield the Path.

    load_dotenv (called inside app.py) does NOT override an already-set env
    var, so monkeypatching SKILLS_DB before AppTest.run() is sufficient to
    isolate every AppTest from the real skills_demo.db.
    """
    db_path = tmp_path / "test_seeded.db"
    seed_demo_db(db_path, n_users=5)  # small seed — faster tests

    # Point the app at the temp DB
    monkeypatch.setenv("SKILLS_DB", str(db_path))

    # Clear the cached connection so app.py opens a fresh one for this DB.
    # @st.cache_resource is process-global; without this, every AppTest after
    # the first would reuse the connection from the first test's DB path.
    st.cache_resource.clear()

    yield db_path


@pytest.fixture()
def seeded_email(seeded_db_path: pathlib.Path) -> str:
    """Return one real email that exists in the seeded database."""
    conn = sqlite3.connect(seeded_db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT email FROM Person p "
        "WHERE EXISTS (SELECT 1 FROM SkillEntry se WHERE se.email = p.email) "
        "LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    assert row is not None, "Seeded DB has no Person rows — check seed_demo_db()"
    return row[0]
