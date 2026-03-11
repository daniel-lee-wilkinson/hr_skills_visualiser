"""
test_db.py — Unit tests for scripts/db.py

All tests use the blank_db fixture (empty schema, fresh SQLite file, no
Streamlit involved). They run in milliseconds.
"""

import pytest

from scripts.db import (
    upsert_person,
    get_existing_skills,
    get_existing_applications,
    upsert_application,
    upsert_skill_entry,
    delete_skill,
)


# ─────────────────────────────────────────────
# Person
# ─────────────────────────────────────────────

def test_upsert_person_creates_row(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "alice@example.com")
    cur.execute("SELECT email FROM Person WHERE email = ?", ("alice@example.com",))
    assert cur.fetchone() is not None


def test_upsert_person_is_idempotent(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "alice@example.com")
    upsert_person(conn, cur, "alice@example.com")  # second call must not raise
    cur.execute("SELECT COUNT(*) FROM Person WHERE email = ?", ("alice@example.com",))
    assert cur.fetchone()[0] == 1


# ─────────────────────────────────────────────
# Skill entries
# ─────────────────────────────────────────────

def test_upsert_skill_entry_creates_row(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "bob@example.com")
    upsert_skill_entry(conn, cur, "bob@example.com", "Python", "Data Engineering", 3, 2, 4, 3)
    cur.execute(
        "SELECT theoretical_level, practical_level, interest, field_proficiency "
        "FROM SkillEntry WHERE email=? AND skill_name=? AND field_of_use=?",
        ("bob@example.com", "Python", "Data Engineering"),
    )
    row = cur.fetchone()
    assert row == (3, 2, 4, 3)


def test_upsert_skill_entry_updates_existing(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "bob@example.com")
    upsert_skill_entry(conn, cur, "bob@example.com", "Python", "Data Engineering", 3, 2, 4, 3)
    upsert_skill_entry(conn, cur, "bob@example.com", "Python", "Data Engineering", 5, 5, 5, 5)
    cur.execute(
        "SELECT theoretical_level, practical_level, interest, field_proficiency "
        "FROM SkillEntry WHERE email=? AND skill_name=? AND field_of_use=?",
        ("bob@example.com", "Python", "Data Engineering"),
    )
    assert cur.fetchone() == (5, 5, 5, 5)


def test_upsert_skill_entry_appends_history_each_call(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "carol@example.com")
    upsert_skill_entry(conn, cur, "carol@example.com", "SQL", "Reporting", 2, 2, 3, 2)
    upsert_skill_entry(conn, cur, "carol@example.com", "SQL", "Reporting", 4, 4, 4, 4)
    cur.execute(
        "SELECT COUNT(*) FROM SkillEntryHistory "
        "WHERE email=? AND skill_name=? AND field_of_use=?",
        ("carol@example.com", "SQL", "Reporting"),
    )
    assert cur.fetchone()[0] == 2  # one entry per upsert call


def test_same_skill_different_fields_are_separate_rows(blank_db):
    """Python in Data Engineering and Python in Reporting are distinct records."""
    conn, cur = blank_db
    upsert_person(conn, cur, "dave@example.com")
    upsert_skill_entry(conn, cur, "dave@example.com", "Python", "Data Engineering", 4, 3, 5, 4)
    upsert_skill_entry(conn, cur, "dave@example.com", "Python", "Reporting", 2, 2, 3, 2)
    cur.execute(
        "SELECT COUNT(*) FROM SkillEntry WHERE email=? AND skill_name=?",
        ("dave@example.com", "Python"),
    )
    assert cur.fetchone()[0] == 2


def test_get_existing_skills_returns_all(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "dave@example.com")
    upsert_skill_entry(conn, cur, "dave@example.com", "Docker", "DevOps", 3, 3, 3, 3)
    upsert_skill_entry(conn, cur, "dave@example.com", "AWS", "DevOps", 2, 2, 2, 2)
    skills = get_existing_skills(cur)
    assert set(skills) == {"Docker", "AWS"}


def test_get_existing_skills_filters_by_term(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "eve@example.com")
    upsert_skill_entry(conn, cur, "eve@example.com", "Power BI", "Reporting", 1, 1, 1, 1)
    upsert_skill_entry(conn, cur, "eve@example.com", "Python", "Data Engineering", 2, 2, 2, 2)
    results = get_existing_skills(cur, term="py")
    assert "Python" in results
    assert "Power BI" not in results


def test_delete_skill_single_removes_only_target(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "frank@example.com")
    upsert_skill_entry(conn, cur, "frank@example.com", "Excel", "Reporting", 3, 3, 3, 3)
    upsert_skill_entry(conn, cur, "frank@example.com", "R", "Statistics", 2, 2, 2, 2)
    delete_skill(conn, cur, "frank@example.com", skill="Excel")
    cur.execute("SELECT skill_name FROM SkillEntry WHERE email=?", ("frank@example.com",))
    remaining = [r[0] for r in cur.fetchall()]
    assert remaining == ["R"]


def test_delete_skill_all_removes_all_for_email(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "grace@example.com")
    upsert_skill_entry(conn, cur, "grace@example.com", "Excel", "Reporting", 3, 3, 3, 3)
    upsert_skill_entry(conn, cur, "grace@example.com", "R", "Statistics", 2, 2, 2, 2)
    delete_skill(conn, cur, "grace@example.com")  # no skill arg = delete all
    cur.execute("SELECT COUNT(*) FROM SkillEntry WHERE email=?", ("grace@example.com",))
    assert cur.fetchone()[0] == 0


def test_delete_skill_also_removes_history(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "hank@example.com")
    upsert_skill_entry(conn, cur, "hank@example.com", "Java", "Backend", 4, 4, 4, 4)
    delete_skill(conn, cur, "hank@example.com", skill="Java")
    cur.execute(
        "SELECT COUNT(*) FROM SkillEntryHistory WHERE email=? AND skill_name=?",
        ("hank@example.com", "Java"),
    )
    assert cur.fetchone()[0] == 0


# ─────────────────────────────────────────────
# Applications
# ─────────────────────────────────────────────

def test_upsert_application_returns_name(blank_db):
    conn, cur = blank_db
    name = upsert_application(conn, cur, "HAZOP")
    assert name == "HAZOP"


def test_upsert_application_is_idempotent(blank_db):
    conn, cur = blank_db
    name1 = upsert_application(conn, cur, "CFD")
    name2 = upsert_application(conn, cur, "CFD")
    assert name1 == name2
    cur.execute("SELECT COUNT(*) FROM Application WHERE name='CFD'")
    assert cur.fetchone()[0] == 1


def test_get_existing_applications_returns_all(blank_db):
    conn, cur = blank_db
    upsert_application(conn, cur, "LCA")
    upsert_application(conn, cur, "HAZOP")
    apps = get_existing_applications(cur)
    names = [name for _, name in apps]
    assert set(names) == {"LCA", "HAZOP"}


def test_get_existing_applications_filters_by_term(blank_db):
    conn, cur = blank_db
    upsert_application(conn, cur, "Process Safety")
    upsert_application(conn, cur, "Optimization")
    results = get_existing_applications(cur, term="process")
    names = [name for _, name in results]
    assert "Process Safety" in names
    assert "Optimization" not in names

