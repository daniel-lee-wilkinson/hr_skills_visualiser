![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

# HR Skills Visualiser

A small internal tool built around one idea: visible skills are usable skills. Colleagues self-assess skills in the context of specific fields of use (e.g. Data Engineering, Process Safety), rating four dimensions per combination: theoretical knowledge, practical experience, interest in developing further, and proficiency within that field. Management gets a company-wide view of expertise, skill gaps, and where knowledge is concentrated or at risk.

Built with Python, Streamlit, and SQLite.

---

## The two apps

The tool is split into two separate web apps to keep personal data away from those who shouldn't see it:

| App | Port | Who uses it |
|-----|------|-------------|
| Employee app | 8501 | All staff — register, view own skills, log updates |
| Management app | 8502 | HR / managers only — full team view, analytics, admin |

Both apps share a single database. All users' data is stored in one place on the server. Each skill entry is tied to a specific field of use, so the same skill can be rated independently in different contexts.

---

## Running it — choose your path

### Option A: Docker (recommended for shared / production use)

Use this if you want multiple people to use the tool. The app runs on a central server; colleagues open it in a browser with nothing to install on their machines.

**Requirements:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine + Compose (Linux) on the server machine.

**1. Clone the repo onto the server**
```bash
git clone https://github.com/daniel-lee-wilkinson/hr_skills_visualiser.git
cd hr_skills_visualiser
```

**2. Build and start**

Open Docker Desktop and run:

```bash
docker compose up --build -d
```
Both services start in the background. On the server itself:
- Employee app → http://localhost:8501
- Management app → http://localhost:8502

Other machines on the same network use the server's IP or hostname instead of `localhost`, e.g. `http://192.168.113.2:8501`.

**3. Tell your users their URLs** — that's all they need.

#### First deploy — seeding demo data
To start with 20 synthetic users pre-loaded, open `docker-compose.yml` and set `SEED_DEMO_DATA: "true"` on the `employee` service before the first `docker compose up --build -d`. Set it back to `"false"` afterwards — re-seeding is skipped automatically once the database file exists.

#### Day-to-day commands
```bash
docker compose up -d       # start both services
docker compose down        # stop both services
docker compose logs -f     # tail live logs from both containers
docker compose up --build -d   # rebuild after code changes (data is preserved)
```

#### Database
The SQLite file is stored in a named Docker volume (`skills_data`) at `/data/skills.db`. It is shared between both containers and survives restarts and rebuilds. To back it up:
```bash
# Windows (PowerShell)
docker run --rm -v hr-skills-visualiser_skills_data:/data -v "${PWD}:/backup" alpine cp /data/skills.db /backup/skills_backup.db
```

---

### Option B: Local development (single machine only)

Use this to explore the code or run tests. The app is served from your own machine and is only accessible to you — not suitable for shared use.

**1. Clone**
```bash
git clone https://github.com/daniel-lee-wilkinson/hr_skills_visualiser.git
cd hr_skills_visualiser
```

**2. Install (once)**
```
install.cmd
```
Creates a virtual environment, installs dependencies, writes a `.env`, and generates `skills_demo.db` with 20 synthetic users.

**3. Run**
```
run_employee_app.cmd      # port 8501
run_management_app.cmd    # port 8502
```
Or directly:
```bash
streamlit run scripts/app_employee.py
streamlit run scripts/app_management.py --server.port 8502
```

**4. Reports (optional)**
```bash
python scripts/query_skills.py
```
Outputs `company_skill_report.xlsx` and `.csv`.

---

## Architecture reference

### App structure
`scripts/app_common.py` handles the DB connection, environment setup, and cached data loaders used by both apps. No paths are hardcoded — the database location is resolved from environment variables at runtime.

### SQLite schema
- `Person`: registered users
- `Application`: fields of use (e.g. Data Engineering, Process Safety)
- `SkillEntry`: current ratings per **(person, skill, field)** — all four dimensions (theoretical, practical, interest, field proficiency) stored together per context
- `SkillEntryHistory`: full history with timestamps, same key — used for the progression chart

Ratings are always field-specific. There is no field-agnostic skill row — rating Python in Data Engineering and Python in Reporting produces two separate records. The progression chart therefore always shows meaningful change over time within one consistent context.

Concurrent access is handled via WAL (Write-Ahead Logging) mode, which allows multiple simultaneous readers without blocking writes.

### Standalone reporting
`scripts/query_skills.py` generates Excel/CSV summaries and heatmaps directly from the database — useful for one-off reports outside the Streamlit UI.

### Docker files

| File | Purpose |
|------|---------|
| `Dockerfile` | Two-stage build — pip dependencies cached separately from source for fast rebuilds |
| `docker-compose.yml` | Two services sharing the `skills_data` named volume |
| `docker-entrypoint.py` | Initialises the DB on first launch, then starts Streamlit |
| `.dockerignore` | Keeps the image small; excludes `.env`, `*.db`, `.venv`, tests, etc. |

---

## Repo structure
```
hr_skills_visualiser/
├── scripts/
│   ├── app_common.py       # shared DB connection, env setup, cached loaders
│   ├── app_employee.py     # employee-facing app
│   ├── app_management.py   # management app
│   ├── db.py               # SQLite CRUD helpers
│   ├── make_demo_db.py     # generates demo database with Faker
│   └── query_skills.py     # standalone reporting script
├── tests/
├── Dockerfile              # container image definition
├── docker-compose.yml      # two-service orchestration (employee + management)
├── docker-entrypoint.py    # DB init + Streamlit launcher for containers
├── .dockerignore
├── install.cmd             # one-time setup (local dev only)
├── run_employee_app.cmd    # local dev launcher
├── run_management_app.cmd  # local dev launcher
├── requirements.txt
└── .gitignore
```

---

## Notes
- `skills_demo.db` is generated by the installer and gitignored. It never contains real data.
- Real databases and generated reports are excluded by `.gitignore`.
- Tests use `tmp_path` fixtures and never touch the demo database.
