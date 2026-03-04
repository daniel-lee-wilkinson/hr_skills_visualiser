"""
test_app.py — AppTest integration tests for scripts/app.py

These tests exercise the real Streamlit script against a temp seeded DB.
The SKILLS_DB env var is redirected by the seeded_db_path fixture before each
test, so the real skills_demo.db is never touched.

Streamlit AppTest docs:
https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest
"""

import sqlite3

import pytest
from streamlit.testing.v1 import AppTest


APP_PATH = "scripts/app.py"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

# AppTest needs a longer timeout on first run due to Python import warm-up.
_TIMEOUT = 60


def fresh_at(seeded_db_path) -> AppTest:
    """Create an AppTest instance and run it once (initial render)."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=_TIMEOUT)
    return at


# ─────────────────────────────────────────────
# Basic load
# ─────────────────────────────────────────────

def test_app_loads_without_error(seeded_db_path):
    """The app must render fully without raising an exception."""
    at = fresh_at(seeded_db_path)
    assert not at.exception


def test_app_title_present(seeded_db_path):
    """Page title element 'Skill Tracker' must be present."""
    at = fresh_at(seeded_db_path)
    titles = [t.value for t in at.title]
    assert any("Skill Tracker" in t for t in titles)


# ─────────────────────────────────────────────
# Home tab  —  email registration
# ─────────────────────────────────────────────

def test_home_continue_registers_email(seeded_db_path):
    """Entering an email and clicking Continue must store it in session state."""
    at = fresh_at(seeded_db_path)
    at.text_input[0].set_value("testuser@example.com")
    at.button(key="home_continue").click()
    at.run(timeout=_TIMEOUT)

    assert not at.exception
    assert at.session_state["email"] == "testuser@example.com"


def test_home_continue_missing_email_shows_error(seeded_db_path):
    """Clicking Continue with no email must raise an st.error (not an exception)."""
    at = fresh_at(seeded_db_path)
    # Leave email blank, just click Continue
    at.button(key="home_continue").click()
    at.run(timeout=_TIMEOUT)

    assert not at.exception
    assert len(at.error) > 0


# ─────────────────────────────────────────────
# My Skills tab  —  data display
# ─────────────────────────────────────────────

def test_my_skills_shows_dataframe_for_seeded_user(seeded_db_path, seeded_email):
    """A seeded user should see their skills listed in a dataframe."""
    at = fresh_at(seeded_db_path)
    # Register the seeded email via the Home tab
    at.text_input[0].set_value(seeded_email)
    at.button(key="home_continue").click()
    at.run(timeout=_TIMEOUT)

    assert not at.exception
    # At least one dataframe should be rendered (the skill table in My Skills)
    assert len(at.dataframe) > 0


# ─────────────────────────────────────────────
# Analytics tab  —  multiselect + data
# ─────────────────────────────────────────────

def test_analytics_multiselect_populated_with_applications(seeded_db_path):
    """The Analytics tab multiselect must contain the seeded application names."""
    at = fresh_at(seeded_db_path)

    assert not at.exception
    assert len(at.multiselect) > 0
    # Seeded applications from make_demo_db
    expected = {"HAZOP", "CFD", "LCA", "Process Safety", "Optimization"}
    # The Management tab adds multiselects before the Analytics one, so search
    # across all multiselects for the one that contains application names.
    all_options = set()
    for ms in at.multiselect:
        all_options.update(ms.options)
    assert expected.issubset(all_options)


# ─────────────────────────────────────────────
# Admin tab  —  delete
# ─────────────────────────────────────────────

def test_admin_delete_removes_skill_from_db(seeded_db_path, seeded_email):
    """Clicking Delete for a known email+skill must remove it from the DB."""
    # Identify a skill the seeded user has
    conn = sqlite3.connect(seeded_db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT skill FROM SkillAssessment WHERE email=? LIMIT 1",
        (seeded_email,),
    )
    row = cur.fetchone()
    conn.close()
    assert row is not None, "Seeded user has no skills"
    target_skill = row[0]

    at = fresh_at(seeded_db_path)
    # Admin tab: first text_input is "Email to modify", second is "Skill to delete"
    # Find them by iterating — they may not be index 0/1 if Home tab input is also rendered
    admin_inputs = [ti for ti in at.text_input if "modify" in ti.label.lower() or "delete" in ti.label.lower()]
    if len(admin_inputs) >= 2:
        admin_inputs[0].set_value(seeded_email)
        admin_inputs[1].set_value(target_skill)
    else:
        # Fallback: use indices (Home input [0], Admin email [1], Admin skill [2])
        at.text_input[1].set_value(seeded_email)
        at.text_input[2].set_value(target_skill)

    at.button(key="delete_btn").click()
    at.run(timeout=_TIMEOUT)

    assert not at.exception

    # Verify directly in the DB
    conn = sqlite3.connect(seeded_db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM SkillAssessment WHERE email=? AND skill=?",
        (seeded_email, target_skill),
    )
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0
