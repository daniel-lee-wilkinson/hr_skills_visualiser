"""
db.py — Pure database layer for the Skill Tracker.

All functions accept an explicit sqlite3 connection and cursor so they can be
used both by the Streamlit app (which holds module-level conn/cur) and by the
test suite (which injects a fresh in-memory or temp-file connection).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS Person (
        email      TEXT PRIMARY KEY,
        first_name TEXT,
        last_name  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS SkillAssessment (
        email              TEXT,
        skill              TEXT,
        theoretical_level  INTEGER CHECK (theoretical_level BETWEEN 1 AND 5),
        practical_level    INTEGER CHECK (practical_level   BETWEEN 1 AND 5),
        interest           INTEGER CHECK (interest          BETWEEN 1 AND 5),
        PRIMARY KEY (email, skill),
        FOREIGN KEY (email) REFERENCES Person(email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS SkillHistory (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        email              TEXT,
        skill              TEXT,
        theoretical_level  INTEGER CHECK (theoretical_level BETWEEN 1 AND 5),
        practical_level    INTEGER CHECK (practical_level   BETWEEN 1 AND 5),
        interest           INTEGER CHECK (interest          BETWEEN 1 AND 5),
        updated_at         TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (email) REFERENCES Person(email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Application (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS SkillApplication (
        email          TEXT,
        skill          TEXT,
        application_id INTEGER,
        level          INTEGER CHECK (level BETWEEN 1 AND 5),
        PRIMARY KEY (email, skill, application_id),
        FOREIGN KEY (email, skill) REFERENCES SkillAssessment(email, skill),
        FOREIGN KEY (application_id) REFERENCES Application(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ApplicationHistory (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        email          TEXT,
        skill          TEXT,
        application_id INTEGER,
        level          INTEGER,
        updated_at     TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (email, skill) REFERENCES SkillAssessment(email, skill),
        FOREIGN KEY (application_id) REFERENCES Application(id)
    )
    """,
]


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables (idempotent — uses CREATE TABLE IF NOT EXISTS)."""
    cur = conn.cursor()
    for ddl in _DDL:
        cur.execute(ddl)
    conn.commit()


# ─────────────────────────────────────────────
# Person
# ─────────────────────────────────────────────

def upsert_person(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    email: str,
    first_name: str = "",
    last_name: str = "",
) -> None:
    cur.execute(
        """
        INSERT INTO Person (email, first_name, last_name)
        VALUES (?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            first_name = CASE WHEN excluded.first_name != '' THEN excluded.first_name ELSE Person.first_name END,
            last_name  = CASE WHEN excluded.last_name  != '' THEN excluded.last_name  ELSE Person.last_name  END
        """,
        (email, first_name or "", last_name or ""),
    )
    conn.commit()


# ─────────────────────────────────────────────
# Skills
# ─────────────────────────────────────────────

def get_existing_skills(cur: sqlite3.Cursor, term: str = "") -> list[str]:
    if term:
        cur.execute(
            "SELECT DISTINCT skill FROM SkillAssessment WHERE LOWER(skill) LIKE ?",
            (f"%{term.lower()}%",),
        )
    else:
        cur.execute("SELECT DISTINCT skill FROM SkillAssessment")
    return [r[0] for r in cur.fetchall()]


def upsert_skill(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    email: str,
    skill: str,
    theo: int,
    prac: int,
    interest: int,
) -> None:
    cur.execute(
        """
        INSERT INTO SkillAssessment (email, skill, theoretical_level, practical_level, interest)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(email, skill) DO UPDATE SET
            theoretical_level = excluded.theoretical_level,
            practical_level   = excluded.practical_level,
            interest          = excluded.interest
        """,
        (email, skill, theo, prac, interest),
    )
    cur.execute(
        """
        INSERT INTO SkillHistory (email, skill, theoretical_level, practical_level, interest, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (email, skill, theo, prac, interest, datetime.now().isoformat()),
    )
    conn.commit()


def delete_skill(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    email: str,
    skill: str | None = None,
) -> None:
    """Delete a single skill (or all skills) for the given email."""
    if skill:
        cur.execute("DELETE FROM SkillAssessment WHERE email=? AND skill=?", (email, skill))
        cur.execute("DELETE FROM SkillHistory WHERE email=? AND skill=?", (email, skill))
    else:
        cur.execute("DELETE FROM SkillAssessment WHERE email=?", (email,))
        cur.execute("DELETE FROM SkillHistory WHERE email=?", (email,))
    conn.commit()


# ─────────────────────────────────────────────
# Applications
# ─────────────────────────────────────────────

def get_existing_applications(
    cur: sqlite3.Cursor, term: str = ""
) -> list[tuple[int, str]]:
    if term:
        cur.execute(
            "SELECT id, name FROM Application WHERE LOWER(name) LIKE ?",
            (f"%{term.lower()}%",),
        )
    else:
        cur.execute("SELECT id, name FROM Application")
    return cur.fetchall()


def upsert_application(
    conn: sqlite3.Connection, cur: sqlite3.Cursor, name: str
) -> int:
    cur.execute(
        "INSERT INTO Application (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
        (name,),
    )
    conn.commit()
    cur.execute("SELECT id FROM Application WHERE name = ?", (name,))
    return cur.fetchone()[0]


def upsert_skill_application(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    email: str,
    skill: str,
    app_id: int,
    level: int,
) -> None:
    cur.execute(
        """
        INSERT INTO SkillApplication (email, skill, application_id, level)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(email, skill, application_id) DO UPDATE SET
            level = excluded.level
        """,
        (email, skill, app_id, level),
    )
    cur.execute(
        """
        INSERT INTO ApplicationHistory (email, skill, application_id, level, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (email, skill, app_id, level, datetime.now().isoformat()),
    )
    conn.commit()
