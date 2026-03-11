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

from scripts.db import create_schema, upsert_skill_entry

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

    # --- Seed Applications (fields of use) ---
    fields_list = ["HAZOP", "CFD", "LCA", "Process Safety", "Optimization"]
    for field in fields_list:
        cur.execute("INSERT OR IGNORE INTO Application (name) VALUES (?)", (field,))
    conn.commit()

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

        for skill in random.sample(skills_list, random.randint(2, 4)):
            for field in random.sample(fields_list, random.randint(1, 2)):
                # Insert 1–3 history points, each slightly varying
                for i in range(random.randint(1, 3)):
                    ts = (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
                    upsert_skill_entry(
                        conn, cur,
                        email, skill, field,
                        theo=random.randint(1, 5),
                        prac=random.randint(1, 5),
                        interest=random.randint(1, 5),
                        field_proficiency=random.randint(1, 5),
                    )
                    # Backdate the last inserted history row
                    cur.execute(
                        "UPDATE SkillEntryHistory SET updated_at=? "
                        "WHERE id=(SELECT MAX(id) FROM SkillEntryHistory WHERE email=? AND skill_name=? AND field_of_use=?)",
                        (ts, email, skill, field),
                    )
                conn.commit()

    conn.close()
    print(f"✅ Demo database created: {db_path}")


if __name__ == "__main__":
    db_path = BASE_DIR / "skills_demo.db"
    seed_demo_db(db_path)

