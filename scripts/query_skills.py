"""
Connects to a SQLite skills assessment database, performs aggregation queries
to analyze company skill strengths, and generates summary reports in Excel, CSV,
and PNG formats. Visualizes average skill levels through bar charts and static heatmaps, 
labels cells with participant counts, and creates an interactive heatmap using Plotly to
present individual and average assessment data. Utilizes environment configuration for
DB location and handles missing data cases gracefully.
"""

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from dotenv import load_dotenv
import pathlib

# ──────────────────────────────
#  Configurable DB path
# ──────────────────────────────
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

DB_FILE = os.getenv("SKILLS_DB", "skills_demo.db")
DB_PATH = BASE_DIR / DB_FILE

print("Querying DB:", DB_PATH)
FILE_PREFIX = "prod_" if "prod" in DB_FILE.lower() else ""

conn = sqlite3.connect(DB_PATH)

# ──────────────────────────────
#  Aggregation query
# ──────────────────────────────
query = """
SELECT 
    skill,
    ROUND(AVG(theoretical_level), 2) AS avg_theoretical,
    ROUND(AVG(practical_level), 2) AS avg_practical,
    ROUND(AVG(interest), 2) AS avg_interest,
    COUNT(email) AS num_people
FROM SkillAssessment
GROUP BY skill
ORDER BY avg_practical DESC, avg_theoretical DESC, avg_interest DESC;
"""
df = pd.read_sql_query(query, conn)

if df.empty:
    print("⚠️ No data in SkillAssessment table. Nothing to plot.")
else:
    # Save report
    df.to_excel(f"{FILE_PREFIX}company_skill_report.xlsx", index=False)
    df.to_csv(f"{FILE_PREFIX}company_skill_report.csv", index=False)
    print(df)

    # ──────────────────────
    # Bar Chart
    # ──────────────────────
    df.plot(x="skill", y=["avg_theoretical", "avg_practical", "avg_interest"], 
            kind="bar", figsize=(10,6))
    plt.title("Company Skill Strengths")
    plt.ylabel("Average Level (1–5)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(f"{FILE_PREFIX}company_skill_report.png")
    plt.show()

    # ──────────────────────
    # Static Heatmap
    # ──────────────────────
    df["avg_all"] = df[["avg_theoretical", "avg_practical", "avg_interest"]].mean(axis=1)
    df = df.sort_values("avg_all", ascending=False)

    heatmap_df = df.set_index("skill")[["avg_theoretical","avg_practical","avg_interest"]]
    headcounts_matrix = pd.concat([df["num_people"]]*heatmap_df.shape[1], axis=1)
    headcounts_matrix.index = heatmap_df.index
    headcounts_matrix.columns = heatmap_df.columns

    plt.figure(figsize=(10, len(df)//2))
    sns.heatmap(
        heatmap_df,
        annot=headcounts_matrix, fmt="d",
        cmap="YlGnBu",
        vmin=1, vmax=5,
        cbar_kws={'label': 'Average Level'}
    )
    plt.title("Company Skills Heatmap (Sorted by Highest Overall Average). Labels = headcount.")
    plt.tight_layout()
    plt.savefig(f"{FILE_PREFIX}company_skill_heatmap.png")
    plt.show()

    # ──────────────────────
    # Interactive Heatmap
    # ──────────────────────
    query = """
    SELECT skill, email, theoretical_level, practical_level, interest
    FROM SkillAssessment;
    """
    df = pd.read_sql_query(query, conn)

    if not df.empty:
        melted = df.melt(id_vars=["skill", "email"],
                        value_vars=["theoretical_level", "practical_level", "interest"],
                        var_name="dimension",
                        value_name="level")

        avg_df = melted.groupby(["skill", "dimension"])["level"].mean().reset_index()
        names = melted.groupby(["skill", "dimension"])["email"].apply(lambda x: "<br>".join(x)).reset_index()
        avg_df = avg_df.merge(names, on=["skill", "dimension"])

        matrix = avg_df.pivot(index="skill", columns="dimension", values="level")
        hover_matrix = avg_df.pivot(index="skill", columns="dimension", values="email")

        fig = go.Figure(data=go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            text=hover_matrix.values,
            hovertemplate="Skill: %{y}<br>Dimension: %{x}<br>Avg Level: %{z:.2f}<br><br>People:<br>%{text}",
            colorscale="YlGnBu",
            zmin=1, zmax=5,
            colorbar=dict(title="Avg Level")
        ))
        fig.update_layout(title="Interactive Skills Heatmap")
        fig.show()

conn.close()