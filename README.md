## Overview
The **Skills Visualiser App** is an internal tool prototype built in **Python** with **Streamlit** and **SQLite**.  
It allows colleagues to:
- Add/update their skills with ratings for theoretical knowledge, practical experience, and interest.  
- Preserve a history of changes for auditability.  
- Generate company-wide skill reports (CSV, Excel, PNG visualisations).  

This repo includes a **synthetic demo dataset** (`skills_demo.db`) generated with Faker. No personal data is stored.  

---

## Why This Matters
Teams often struggle to keep track of colleagues’ skills in a structured, version-controlled way.  
This app demonstrates how lightweight internal tools can solve that by:
- Allowing colleagues to self-assess skills and keep them up-to-date.  
- Preserving **history of changes**, so managers can see growth over time.  
- Providing **company-wide reporting** that supports resource allocation, training decisions, and project staffing.  
- Showing how Python, Streamlit, and SQLite can be combined to quickly prototype useful internal systems.  

Although this repo uses demo data, the same approach could scale to PostgreSQL or integrate with enterprise tools like Power BI or HR systems.

---

### **Streamlit Frontend**
Split into two separate apps — see [App Architecture](#app-architecture--data-protection-split) below.

### **SQLite Backend**
- `Person`: unique users.  
- `SkillAssessment`: current skill ratings.  
- `SkillHistory`: all changes with timestamps for audit trail.  

### **Reporting Script** (`query_skills.py`)
- Uses environment config (`.env`) to select DB (`skills_demo.db` or `prod_skills.db`).  
- Handles **empty DBs gracefully** (no crashes if no data).  
- Generates:  
  - Excel + CSV reports.  
  - Bar charts of skill strengths.  
  - Static seaborn heatmaps (with headcounts in each cell).  
  - Interactive Plotly heatmaps (hover to see contributors).  
- Applies `prod_` prefix to output files when using `prod_skills.db`.

### **Demo Data Generator** (`make_demo_db.py`)
- Creates `skills_demo.db` with 20 fake users and 2–4 random skills each.  
- Populates **SkillAssessment** and **SkillHistory** with random values.  
- Ensures the app runs out-of-the-box with synthetic data.

---

## App Architecture — Data Protection Split

The Streamlit front-end is split into **two separate apps** to keep personal data away from employees who should not see it:

| App | Script | Launcher | Default port | Who uses it |
|-----|--------|----------|-------------|-------------|
| **Employee app** | `scripts/app_employee.py` | `run_employee_app.cmd` | 8501 | All employees |
| **Management app** | `scripts/app_management.py` | `run_management_app.cmd` | 8502 | HR / managers only |

### Employee app tabs
- **Home** – register / confirm email
- **My Skills** – view *your own* skill profile only
- **My Progression** – track how *your own* skills have changed over time
- **Add / Update Skills** – log or update a skill entry

### Management app tabs
- **Management** – individual breakdown of every person's self-assessed values
- **Analytics** – aggregated company-wide charts, gap analysis, and export to Excel/CSV
- **Admin** – delete skill entries (maintenance)

### Shared infrastructure
`scripts/app_common.py` contains the DB connection, environment/path setup, and cached data loaders used by both apps. Configuration comes from the local `.env`. For production, `install.cmd` writes a `SKILLS_ENV_PATH` entry into `.env` pointing at a second `.env` on the shared drive — no private paths are hardcoded in the source code.

> **Deployment tip**: run the two apps on different ports (defaults above) so they can coexist on the same machine simultaneously. Use OS-level access controls (e.g. different Windows user groups, a reverse proxy, or VPN) to restrict who can reach port 8502.

---

## Who Can Use This
- **Data teams** – as a template for building internal tools that collect structured data from colleagues.  
- **HR or management** – to track skills, identify training needs, or plan project staffing.  
- **Developers** – as an example of building a CRUD app with Streamlit + SQLite.  
- **Students/learners** – as a reproducible portfolio project that goes beyond simple dashboards.  

---

## Repo Structure
```
hr_skills_visualiser/
├── scripts/
│   ├── app_common.py       # Shared DB connection, env setup, cached loaders
│   ├── app_employee.py     # Employee-facing app (own data only)
│   ├── app_management.py   # Management app (all data, analytics, admin)
│   ├── db.py               # SQLite CRUD helpers
│   ├── make_demo_db.py     # Generates fake SQLite DB with Faker
│   └── query_skills.py     # Standalone reporting script (static charts)
├── install.cmd             # One-time setup (venv, packages, shared DB config)
├── run_employee_app.cmd    # Launcher → app_employee.py (port 8501)
├── run_management_app.cmd  # Launcher → app_management.py (port 8502)
├── skills_demo.db          # Demo database with synthetic users & skills
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Usage

### 1. Clone the repo
```bash
git clone https://github.com/your-username/skills-visualiser-app.git
cd skills-visualiser-app
```

### 2. Run the installer (once per machine)
```
install.cmd
```
This will:
- Create a Python virtual environment and install all dependencies
- Write a local `.env` pointing at the demo database
- Optionally configure a **shared production database** on a mapped network drive (e.g. `C:\Skills_Tracker\` or a UNC path like `\\server\Skills_Tracker\`)

When prompted about the shared DB:
- Choose **Y** on the first machine with the shared drive mapped — you will be prompted for the folder path and DB filename; the installer creates the DB and writes a `.env` there
- Choose **Y** on every subsequent machine and enter the same shared path — the installer adds `SKILLS_ENV_PATH` to the local `.env` so the app finds the production DB automatically
- Choose **N** on dev/test machines to stay on the local demo database

### 3. Run the apps

**Employee app** (port 8501 — for all staff):
```bash
# Windows
run_employee_app.cmd
# or directly
streamlit run scripts/app_employee.py
```

**Management app** (port 8502 — restricted to HR/managers):
```bash
# Windows
run_management_app.cmd
# or directly
streamlit run scripts/app_management.py --server.port 8502
```

Both apps connect to `skills_demo.db` by default.  

To point at a different database:
```bash
SKILLS_DB=my_skills.db streamlit run scripts/app_employee.py
```

### 4. Generate reports
```bash
python query_skills.py
```
This produces:
- `company_skill_report.xlsx`  
- `company_skill_report.csv`  

---

## Example Output

**Company Skill Report (aggregated)**  
| skill     | avg_theoretical | avg_practical | avg_interest | num_people |
|-----------|-----------------|---------------|--------------|------------|
| Python    | 4.2             | 3.8           | 4.5          | 12         |
| SQL       | 3.9             | 3.5           | 4.1          | 15         |
| Docker    | 2.8             | 2.6           | 3.0          | 7          |

---

## Notes
- The included database (`skills_demo.db`) is **synthetic**, generated with [Faker](https://faker.readthedocs.io/).  
- Do **not** commit real `skills.db` or reports containing personal data.  
- `.gitignore` excludes private DBs and generated outputs.  

---

## Future Enhancements
- Migration to PostgreSQL for multi-user deployment.  
- Integration with Power BI or Looker dashboards.  
- Advanced filtering and search capabilities in Streamlit.  
- Dockerized deployment.  

---
