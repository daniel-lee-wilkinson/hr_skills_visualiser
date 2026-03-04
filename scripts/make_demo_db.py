# make_demo_db.py
"""
Generates a demo SQLite database populated with fake skill data.

Can be run directly:
    python scripts/make_demo_db.py

Or imported by tests / other scripts:
    from scripts.make_demo_db import seed_demo_db
    seed_demo_db(Path("/tmp/test.db"))
"""

import sqlite3
from faker import Faker
import random
from datetime import datetime, timedelta
import pathlib

from scripts.db import create_schema

fake = Faker()

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent


def seed_demo_db(db_path: pathlib.Path, n_users: int = 20) -> None:
    """Create schema and populate *db_path* with fake data.

    Safe to call on a fresh (non-existent) file. Calling on an existing file
    with data will silently skip duplicate Person rows but may add extra
    history rows, so prefer a clean path for tests.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # --- Create schema ---
    create_schema(conn)

    # --- Seed Applications ---
    applications_list = ["HAZOP", "CFD", "LCA", "Process Safety", "Optimization"]
    for app in applications_list:
        cur.execute("INSERT OR IGNORE INTO Application (name) VALUES (?)", (app,))

    # --- Generate fake data ---
    skills_list = [
        "Python", "SQL", "R", "Docker", "AWS",
        "Excel", "Power BI", "Streamlit", "Java", "C++",
    ]

    for _ in range(n_users):
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()

        cur.execute(
            "INSERT OR IGNORE INTO Person (email, first_name, last_name) VALUES (?, ?, ?)",
            (email, first_name, last_name),
        )

        cur.execute("SELECT id, name FROM Application")
        apps = cur.fetchall()

        for skill in random.sample(skills_list, random.randint(2, 4)):
            theo = random.randint(1, 5)
            prac = random.randint(1, 5)
            interest = random.randint(1, 5)

            cur.execute(
                """
                INSERT OR IGNORE INTO SkillAssessment
                    (email, skill, theoretical_level, practical_level, interest)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email, skill, theo, prac, interest),
            )

            for _ in range(random.randint(1, 3)):
                cur.execute(
                    """
                    INSERT INTO SkillHistory
                        (email, skill, theoretical_level, practical_level, interest, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email, skill,
                        random.randint(1, 5),
                        random.randint(1, 5),
                        random.randint(1, 5),
                        (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
                    ),
                )

            for app_id, app_name in random.sample(apps, random.randint(1, 2)):
                level = random.randint(1, 5)
                cur.execute(
                    """
                    INSERT OR IGNORE INTO SkillApplication
                        (email, skill, application_id, level)
                    VALUES (?, ?, ?, ?)
                    """,
                    (email, skill, app_id, level),
                )

                for _ in range(random.randint(1, 2)):
                    cur.execute(
                        """
                        INSERT INTO ApplicationHistory
                            (email, skill, application_id, level, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            email, skill, app_id,
                            random.randint(1, 5),
                            (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
                        ),
                    )

    conn.commit()
    conn.close()
    print(f"✅ Demo database created: {db_path}")


if __name__ == "__main__":
    db_path = BASE_DIR / "skills_demo.db"
    seed_demo_db(db_path)

