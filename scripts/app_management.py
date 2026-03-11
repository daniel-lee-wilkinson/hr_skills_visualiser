"""
app_management.py – Management / HR Skill Tracker.

Tabs available to authorised managers / HR:
  • Management  – individual breakdown (who said what)
  • Analytics   – aggregated company-level skill analytics and gap reports
  • Admin       – maintenance (delete skills / entries)

Contains personal data — restrict access to authorised personnel only.
Run with:
    streamlit run scripts/app_management.py
"""
import sys
import io
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st
import plotly.express as px

from scripts.app_common import (
    DB_PATH,
    get_connection,
    delete_skill,
    load_analytics_data,
    load_individual_data,
    load_applications,
)

# ─────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────
conn = get_connection()

# ─────────────────────────────────────────────
# App config
# ─────────────────────────────────────────────
st.set_page_config(page_title="Skill Tracker – Management", layout="wide")
st.title("Skill Tracker — Management View")
st.caption(f"Database: `{DB_PATH}`")

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_management, tab_analytics, tab_admin = st.tabs(
    ["Management", "Analytics", "Admin"]
)


# ─────────────────────────────────────────────
# TAB: MANAGEMENT  (individual breakdown — who said what)
# ─────────────────────────────────────────────
with tab_management:
    st.subheader("Individual Skill Entries")
    st.caption("Shows every person's self-assessed values. Use the filters to drill down.")

    ind_df = load_individual_data(conn)

    if ind_df.empty:
        st.info("No skill data in the database yet.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            all_skills = sorted(ind_df["skill"].unique().tolist())
            skill_filter = st.multiselect(
                "Filter by skill:", all_skills, default=[], key="mgmt_skill_filter"
            )
        with col_f2:
            all_people = sorted(ind_df["email"].unique().tolist())
            person_filter = st.multiselect(
                "Filter by person (email):", all_people, default=[], key="mgmt_person_filter"
            )

        view = ind_df.copy()
        if skill_filter:
            view = view[view["skill"].isin(skill_filter)]
        if person_filter:
            view = view[view["email"].isin(person_filter)]

        view = view.rename(columns={
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": "Email",
            "skill": "Skill",
            "field_of_use": "Field of Use",
            "theoretical_level": "Theoretical",
            "practical_level": "Practical",
            "interest": "Interest",
            "field_proficiency": "Proficiency in Field",
        })

        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True,
            column_order=["First Name", "Last Name", "Email", "Skill",
                          "Field of Use", "Theoretical", "Practical",
                          "Interest", "Proficiency in Field"],
        )
        st.caption(
            f"{len(view)} rows shown "
            f"({ind_df['email'].nunique()} people, {ind_df['skill'].nunique()} distinct skills)"
        )


# ─────────────────────────────────────────────
# TAB: ANALYTICS  (aggregated charts + gap visualisations)
# ─────────────────────────────────────────────
with tab_analytics:
    st.subheader("Company Skill Analytics")

    all_apps = load_applications(conn)

    selected = st.multiselect(
        "Filter by field of use:",
        all_apps,
        default=all_apps,
    )

    df = load_analytics_data(conn)

    if selected:
        df = df[df["field_of_use"].isin(selected)]

    if df.empty:
        st.info("No data for the selected filters.")
    else:
        # ── Aggregation ───────────────────────────────
        grouped = df.groupby("skill").agg(
            avg_theoretical=("theoretical_level", "mean"),
            avg_practical=("practical_level", "mean"),
            avg_interest=("interest", "mean"),
            avg_field_proficiency=("field_proficiency", "mean"),
            contributors=("email", "count"),
        ).reset_index()

        for col in ["avg_theoretical", "avg_practical", "avg_interest", "avg_field_proficiency"]:
            grouped[col] = grouped[col].round(1)

        grouped["gap_T_minus_P"] = (grouped["avg_theoretical"] - grouped["avg_practical"]).round(1)
        grouped["gap_I_minus_P"] = (grouped["avg_interest"] - grouped["avg_practical"]).round(1)

        # ── Main summary table ────────────────────────
        st.subheader("Skill Overview (with gaps)")
        st.dataframe(grouped, use_container_width=True)

        # ── Grouped bar: T / P / I ────────────────────
        st.subheader("Average Skill Levels (Theoretical / Practical / Interest)")

        long_form = grouped.melt(
            id_vars="skill",
            value_vars=["avg_theoretical", "avg_practical", "avg_interest", "avg_field_proficiency"],
            var_name="dimension",
            value_name="average",
        )
        long_form["dimension"] = long_form["dimension"].replace({
            "avg_theoretical": "Theoretical",
            "avg_practical": "Practical",
            "avg_interest": "Interest",
            "avg_field_proficiency": "Field Proficiency",
        })

        fig_levels = px.bar(
            long_form,
            x="skill",
            y="average",
            color="dimension",
            barmode="group",
            title="Average Skill Levels by Dimension",
            labels={"average": "Average Level (1–5)", "skill": "Skill"},
            color_discrete_map={
                "Theoretical": "#1f77b4",
                "Practical": "#2ca02c",
                "Interest": "#ff7f0e",
                "Field Proficiency": "#9467bd",
            },
        )
        fig_levels.update_layout(xaxis_tickangle=-45, height=600)
        st.plotly_chart(fig_levels, use_container_width=True)

        # ── Knowledge gap bar chart (T − P) ──────────
        st.subheader("Knowledge Gaps (Theoretical − Practical)")

        grouped_sorted_gap = grouped.sort_values("gap_T_minus_P", ascending=False)

        fig_gap = px.bar(
            grouped_sorted_gap,
            x="skill",
            y="gap_T_minus_P",
            title="Knowledge Gap per Skill (T − P)",
            labels={"gap_T_minus_P": "Gap (Theoretical − Practical)", "skill": "Skill"},
        )
        fig_gap.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig_gap, use_container_width=True)

        st.caption(
            "Positive values: people understand the topic better than they can apply it. "
            "Negative values: practical capability exceeds theoretical (rare but possible)."
        )

        # ── Gap snapshot tables ───────────────────────
        st.subheader("Gap Snapshots")

        colA, colB, colC = st.columns(3)

        with colA:
            st.markdown("### Top Knowledge Gaps (T − P)")
            st.dataframe(
                grouped.sort_values("gap_T_minus_P", ascending=False)
                [["skill", "avg_theoretical", "avg_practical", "gap_T_minus_P"]]
                .head(10),
                use_container_width=True,
            )

        with colB:
            st.markdown("### Top Motivation Gaps (I − P)")
            st.dataframe(
                grouped.sort_values("gap_I_minus_P", ascending=False)
                [["skill", "avg_interest", "avg_practical", "gap_I_minus_P"]]
                .head(10),
                use_container_width=True,
            )

        with colC:
            st.markdown("### Lowest Practical Capability")
            st.dataframe(
                grouped.sort_values("avg_practical", ascending=True)
                [["skill", "avg_practical", "avg_theoretical", "avg_interest"]]
                .head(10),
                use_container_width=True,
            )

        # ── Export ────────────────────────────────────
        st.markdown("#### Download Reports")
        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                label="⬇ Download CSV",
                data=grouped.to_csv(index=False).encode("utf-8"),
                file_name="company_skill_report_with_gaps.csv",
                mime="text/csv",
            )
        with dl_col2:
            _xlsx_buf = io.BytesIO()
            grouped.to_excel(_xlsx_buf, index=False)
            st.download_button(
                label="⬇ Download Excel",
                data=_xlsx_buf.getvalue(),
                file_name="company_skill_report_with_gaps.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ─────────────────────────────────────────────
# TAB: ADMIN  (maintenance)
# ─────────────────────────────────────────────
with tab_admin:
    st.subheader("Admin / Maintenance")

    del_email = st.text_input("Email to modify")
    del_skill = st.text_input("Skill to delete (leave blank to delete all skills for this email)")

    if st.button("Delete", key="delete_btn"):
        if del_email:
            delete_skill(conn, del_email, del_skill if del_skill else None)
            st.success("Delete operation complete.")
        else:
            st.error("Enter an email first.")
