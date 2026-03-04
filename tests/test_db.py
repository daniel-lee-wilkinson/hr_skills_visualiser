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
    upsert_skill,
    upsert_skill_application,
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
# Skills
# ─────────────────────────────────────────────

def test_upsert_skill_creates_row(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "bob@example.com")
    upsert_skill(conn, cur, "bob@example.com", "Python", 3, 2, 4)
    cur.execute(
        "SELECT theoretical_level, practical_level, interest "
        "FROM SkillAssessment WHERE email=? AND skill=?",
        ("bob@example.com", "Python"),
    )
    row = cur.fetchone()
    assert row == (3, 2, 4)


def test_upsert_skill_updates_existing(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "bob@example.com")
    upsert_skill(conn, cur, "bob@example.com", "Python", 3, 2, 4)
    upsert_skill(conn, cur, "bob@example.com", "Python", 5, 5, 5)  # update
    cur.execute(
        "SELECT theoretical_level, practical_level, interest "
        "FROM SkillAssessment WHERE email=? AND skill=?",
        ("bob@example.com", "Python"),
    )
    assert cur.fetchone() == (5, 5, 5)


def test_upsert_skill_appends_history_each_call(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "carol@example.com")
    upsert_skill(conn, cur, "carol@example.com", "SQL", 2, 2, 3)
    upsert_skill(conn, cur, "carol@example.com", "SQL", 4, 4, 4)
    cur.execute(
        "SELECT COUNT(*) FROM SkillHistory WHERE email=? AND skill=?",
        ("carol@example.com", "SQL"),
    )
    assert cur.fetchone()[0] == 2  # one entry per upsert call


def test_get_existing_skills_returns_all(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "dave@example.com")
    upsert_skill(conn, cur, "dave@example.com", "Docker", 3, 3, 3)
    upsert_skill(conn, cur, "dave@example.com", "AWS", 2, 2, 2)
    skills = get_existing_skills(cur)
    assert set(skills) == {"Docker", "AWS"}


def test_get_existing_skills_filters_by_term(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "eve@example.com")
    upsert_skill(conn, cur, "eve@example.com", "Power BI", 1, 1, 1)
    upsert_skill(conn, cur, "eve@example.com", "Python", 2, 2, 2)
    results = get_existing_skills(cur, term="py")
    assert "Python" in results
    assert "Power BI" not in results


def test_delete_skill_single_removes_only_target(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "frank@example.com")
    upsert_skill(conn, cur, "frank@example.com", "Excel", 3, 3, 3)
    upsert_skill(conn, cur, "frank@example.com", "R", 2, 2, 2)
    delete_skill(conn, cur, "frank@example.com", skill="Excel")
    cur.execute("SELECT skill FROM SkillAssessment WHERE email=?", ("frank@example.com",))
    remaining = [r[0] for r in cur.fetchall()]
    assert remaining == ["R"]


def test_delete_skill_all_removes_all_for_email(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "grace@example.com")
    upsert_skill(conn, cur, "grace@example.com", "Excel", 3, 3, 3)
    upsert_skill(conn, cur, "grace@example.com", "R", 2, 2, 2)
    delete_skill(conn, cur, "grace@example.com")  # no skill arg = delete all
    cur.execute("SELECT COUNT(*) FROM SkillAssessment WHERE email=?", ("grace@example.com",))
    assert cur.fetchone()[0] == 0


def test_delete_skill_also_removes_history(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "hank@example.com")
    upsert_skill(conn, cur, "hank@example.com", "Java", 4, 4, 4)
    delete_skill(conn, cur, "hank@example.com", skill="Java")
    cur.execute(
        "SELECT COUNT(*) FROM SkillHistory WHERE email=? AND skill=?",
        ("hank@example.com", "Java"),
    )
    assert cur.fetchone()[0] == 0


# ─────────────────────────────────────────────
# Applications
# ─────────────────────────────────────────────

def test_upsert_application_returns_integer_id(blank_db):
    conn, cur = blank_db
    app_id = upsert_application(conn, cur, "HAZOP")
    assert isinstance(app_id, int)


def test_upsert_application_is_idempotent_same_id(blank_db):
    conn, cur = blank_db
    id1 = upsert_application(conn, cur, "CFD")
    id2 = upsert_application(conn, cur, "CFD")
    assert id1 == id2


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


# ─────────────────────────────────────────────
# SkillApplication
# ─────────────────────────────────────────────

def test_upsert_skill_application_creates_row_and_history(blank_db):
    conn, cur = blank_db
    upsert_person(conn, cur, "ida@example.com")
    upsert_skill(conn, cur, "ida@example.com", "Streamlit", 4, 3, 5)
    app_id = upsert_application(conn, cur, "Demo App")
    upsert_skill_application(conn, cur, "ida@example.com", "Streamlit", app_id, 4)

    cur.execute(
        "SELECT level FROM SkillApplication WHERE email=? AND skill=? AND application_id=?",
        ("ida@example.com", "Streamlit", app_id),
    )
    assert cur.fetchone() == (4,)

    cur.execute(
        "SELECT COUNT(*) FROM ApplicationHistory WHERE email=? AND skill=?",
        ("ida@example.com", "Streamlit"),
    )
    assert cur.fetchone()[0] == 1
