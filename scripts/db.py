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
    CREATE TABLE IF NOT EXISTS Application (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS SkillEntry (
        email              TEXT,
        skill_name         TEXT,
        field_of_use       TEXT,
        theoretical_level  INTEGER CHECK (theoretical_level BETWEEN 1 AND 5),
        practical_level    INTEGER CHECK (practical_level   BETWEEN 1 AND 5),
        interest           INTEGER CHECK (interest          BETWEEN 1 AND 5),
        field_proficiency  INTEGER CHECK (field_proficiency BETWEEN 1 AND 5),
        PRIMARY KEY (email, skill_name, field_of_use),
        FOREIGN KEY (email) REFERENCES Person(email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS SkillEntryHistory (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        email              TEXT,
        skill_name         TEXT,
        field_of_use       TEXT,
        theoretical_level  INTEGER CHECK (theoretical_level BETWEEN 1 AND 5),
        practical_level    INTEGER CHECK (practical_level   BETWEEN 1 AND 5),
        interest           INTEGER CHECK (interest          BETWEEN 1 AND 5),
        field_proficiency  INTEGER CHECK (field_proficiency BETWEEN 1 AND 5),
        updated_at         TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (email) REFERENCES Person(email)
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
# Skill entries  (current ratings per person/skill/field)
# ─────────────────────────────────────────────

def get_existing_skills(cur: sqlite3.Cursor, term: str = "") -> list[str]:
    if term:
        cur.execute(
            "SELECT DISTINCT skill_name FROM SkillEntry WHERE LOWER(skill_name) LIKE ?",
            (f"%{term.lower()}%",),
        )
    else:
        cur.execute("SELECT DISTINCT skill_name FROM SkillEntry")
    return [r[0] for r in cur.fetchall()]


def upsert_skill_entry(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    email: str,
    skill: str,
    field: str,
    theo: int,
    prac: int,
    interest: int,
    field_proficiency: int,
) -> None:
    """Upsert the current rating for (email, skill, field) and append a history row."""
    cur.execute(
        """
        INSERT INTO SkillEntry
            (email, skill_name, field_of_use,
             theoretical_level, practical_level, interest, field_proficiency)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(email, skill_name, field_of_use) DO UPDATE SET
            theoretical_level = excluded.theoretical_level,
            practical_level   = excluded.practical_level,
            interest          = excluded.interest,
            field_proficiency = excluded.field_proficiency
        """,
        (email, skill, field, theo, prac, interest, field_proficiency),
    )
    cur.execute(
        """
        INSERT INTO SkillEntryHistory
            (email, skill_name, field_of_use,
             theoretical_level, practical_level, interest, field_proficiency, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (email, skill, field, theo, prac, interest, field_proficiency,
         datetime.now().isoformat()),
    )
    conn.commit()


def delete_skill(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    email: str,
    skill: str | None = None,
) -> None:
    """Delete a single skill (all fields) or all skills for the given email."""
    if skill:
        cur.execute("DELETE FROM SkillEntry WHERE email=? AND skill_name=?", (email, skill))
        cur.execute("DELETE FROM SkillEntryHistory WHERE email=? AND skill_name=?", (email, skill))
    else:
        cur.execute("DELETE FROM SkillEntry WHERE email=?", (email,))
        cur.execute("DELETE FROM SkillEntryHistory WHERE email=?", (email,))
    conn.commit()


# ─────────────────────────────────────────────
# Applications  (field-of-use lookup table)
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
) -> str:
    """Ensure the field name exists in Application and return the name."""
    cur.execute(
        "INSERT INTO Application (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
        (name,),
    )
    conn.commit()
    return name
