"""
app_employee.py – Employee-facing Skill Tracker.

Tabs available to every employee:
  • Home            – register your email
  • My Skills       – view your own skill profile
  • My Progression  – track how your skills have changed over time
  • Add / Update    – log or update a skill entry

No other employees' data is accessible here.
Run with:
    streamlit run scripts/app_employee.py
"""
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import streamlit as st
import plotly.express as px

from scripts.app_common import (
    DB_PATH,
    get_connection,
    upsert_person,
    get_existing_skills,
    get_existing_applications,
    upsert_application,
    upsert_skill_entry,
)

# ─────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────
conn = get_connection()

# ─────────────────────────────────────────────
# App config
# ─────────────────────────────────────────────
st.set_page_config(page_title="Skill Tracker – My Skills", layout="wide")
st.title("Skill Tracker")
st.caption(f"Database: `{DB_PATH}`")

# Session-level email
if "email" not in st.session_state:
    st.session_state.email = ""

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_home, tab_myskills, tab_progress, tab_update = st.tabs(
    ["Home", "My Skills", "My Progression", "Add / Update Skills"]
)


# ─────────────────────────────────────────────
# TAB: HOME
# ─────────────────────────────────────────────
with tab_home:
    st.subheader("Start Here")

    with st.form("home_form"):
        email_input = st.text_input(
            "Work email address",
            value=st.session_state.email,
            placeholder="you@company.com",
        )
        col_fn, col_ln = st.columns(2)
        with col_fn:
            first_name_input = st.text_input(
                "First name",
                value=st.session_state.get("first_name", ""),
                placeholder="e.g. Jane",
            )
        with col_ln:
            last_name_input = st.text_input(
                "Last name",
                value=st.session_state.get("last_name", ""),
                placeholder="e.g. Smith",
            )
        home_submitted = st.form_submit_button("Continue", type="primary")

    if home_submitted:
        if email_input:
            st.session_state.email = email_input
            st.session_state.first_name = first_name_input
            st.session_state.last_name = last_name_input
            upsert_person(conn, email_input, first_name_input, last_name_input)
            st.success("Details saved. Go to **My Skills** or **Add / Update Skills**.")
        else:
            st.error("Please enter your email address first.")


# ─────────────────────────────────────────────
# TAB: MY SKILLS
# ─────────────────────────────────────────────
with tab_myskills:
    st.subheader("Your Skill Profile")

    if not st.session_state.email:
        st.info("Enter your email in the 'Home' tab to continue.")
    else:
        email = st.session_state.email
        df = pd.read_sql_query(
            "SELECT skill_name AS skill, field_of_use, "
            "theoretical_level, practical_level, interest, field_proficiency "
            "FROM SkillEntry WHERE email=? ORDER BY skill_name, field_of_use",
            conn,
            params=(email,),
        )

        if df.empty:
            st.info("You have no logged skills yet.")
        else:
            st.dataframe(df, use_container_width=True)


# ─────────────────────────────────────────────
# TAB: MY PROGRESSION
# ─────────────────────────────────────────────
with tab_progress:
    st.subheader("Your Skill Progression Over Time")

    if not st.session_state.email:
        st.info("Enter your email in the Home tab to continue.")
    else:
        email = st.session_state.email

        hist = pd.read_sql_query(
            """
            SELECT skill_name, field_of_use,
                   theoretical_level, practical_level, interest, field_proficiency,
                   updated_at
            FROM SkillEntryHistory
            WHERE email = ?
            ORDER BY updated_at ASC
            """,
            conn,
            params=(email,),
        )

        if hist.empty:
            st.info("No skill history recorded yet.")
        else:
            hist["updated_at"] = pd.to_datetime(hist["updated_at"], errors="coerce")

            # Step 1 — pick a field of use
            fields = sorted(hist["field_of_use"].unique().tolist())
            selected_field = st.selectbox(
                "Select a field of use:", fields, key="prog_field"
            )

            # Step 2 — pick a skill within that field
            field_hist = hist[hist["field_of_use"] == selected_field]
            skills = sorted(field_hist["skill_name"].unique().tolist())
            selected_skill = st.selectbox(
                "Select a skill:", skills, key="prog_skill"
            )

            skill_df = field_hist[field_hist["skill_name"] == selected_skill].copy()

            long_df = skill_df.melt(
                id_vars=["updated_at"],
                value_vars=[
                    "theoretical_level", "practical_level",
                    "interest", "field_proficiency",
                ],
                var_name="dimension",
                value_name="level",
            )

            rename_map = {
                "theoretical_level": "Theoretical",
                "practical_level": "Practical",
                "interest": "Interest",
                "field_proficiency": f"Proficiency in {selected_field}",
            }
            long_df["dimension"] = long_df["dimension"].replace(rename_map)

            st.markdown(
                f"### Progression for **{selected_skill}** in **{selected_field}**"
            )

            fig = px.line(
                long_df,
                x="updated_at",
                y="level",
                color="dimension",
                markers=True,
                title=f"{selected_skill} ({selected_field}) — Progression Over Time",
                labels={"level": "Level (1–5)", "updated_at": "Date"},
                color_discrete_map={
                    "Theoretical": "#1f77b4",
                    "Practical": "#2ca02c",
                    "Interest": "#ff7f0e",
                    f"Proficiency in {selected_field}": "#9467bd",
                },
            )
            fig.update_layout(height=500, yaxis=dict(dtick=1, range=[1, 5]))
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Show raw history data"):
                st.dataframe(skill_df, use_container_width=True)


# ─────────────────────────────────────────────
# TAB: ADD / UPDATE SKILLS
# ─────────────────────────────────────────────
with tab_update:
    st.subheader("Add or Update a Skill")

    if not st.session_state.email:
        st.info("Enter your email in the 'Home' tab first.")
    else:
        email = st.session_state.email
        ADD_NEW = "＋ Add new…"

        # ── Field of Use ──────────────────────────────────────────────────────
        # The selectboxes live OUTSIDE the form so that selecting "＋ Add new…"
        # immediately reveals a text input on the next rerun — before the user
        # touches the sliders.
        st.markdown("#### Field of Use")
        st.caption(
            "The area or context in which you apply this skill — "
            "e.g. *Data Engineering*, *Optimisation*, *Reporting*. "
            "Type to search existing fields; choose **＋ Add new…** if yours isn't listed."
        )
        existing_fields = get_existing_applications(conn, "")
        field_options = [ADD_NEW] + [name for _, name in existing_fields]
        selected_field_option = st.selectbox(
            "Field of use", field_options, key="field_selectbox", label_visibility="collapsed"
        )
        if selected_field_option == ADD_NEW:
            new_field = st.text_input("New field name", placeholder="e.g. Data Engineering")
            field_name = new_field.strip()
        else:
            field_name = selected_field_option

        st.divider()

        # ── Skill ─────────────────────────────────────────────────────────────
        st.markdown("#### Skill")
        st.caption(
            "The specific skill you want to rate. "
            "Type to search existing skills; choose **＋ Add new…** to add one."
        )
        existing_skills = get_existing_skills(conn, "")
        skill_options = [ADD_NEW] + existing_skills
        selected_skill_option = st.selectbox(
            "Skill", skill_options, key="skill_selectbox", label_visibility="collapsed"
        )
        if selected_skill_option == ADD_NEW:
            new_skill = st.text_input("New skill name", placeholder="e.g. Python")
            skill_name = new_skill.strip()
        else:
            skill_name = selected_skill_option

        st.divider()

        # ── Ratings — wrapped in a form to prevent slider reruns ─────────────
        st.markdown("#### Ratings")
        with st.form("skill_ratings_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                theo = st.slider(
                    "Theoretical knowledge", 1, 5, 3,
                    help="How well do you understand the underlying concepts?"
                )
            with col2:
                prac = st.slider(
                    "Practical experience", 1, 5, 3,
                    help="How regularly do you apply this skill day-to-day?"
                )
            with col3:
                interest = st.slider(
                    "Interest / motivation", 1, 5, 3,
                    help="How keen are you to develop this skill further?"
                )

            field_label = field_name if field_name else "this field"
            field_level = st.slider(
                f"Proficiency in {field_label}",
                1, 5, 3,
                help=f"How proficient are you when applying this skill specifically in {field_label}?"
            )

            submitted = st.form_submit_button("Save", type="primary")

        if submitted:
            if not field_name:
                st.error("Please select or enter a field of use.")
            elif not skill_name:
                st.error("Please select or enter a skill name.")
            else:
                upsert_application(conn, field_name)
                upsert_skill_entry(
                    conn, email, skill_name, field_name,
                    theo, prac, interest, field_level
                )
                st.session_state.save_success = f"Saved **{skill_name}** in the field of **{field_name}**."
                st.rerun()

        if st.session_state.get("save_success"):
            st.success(st.session_state.pop("save_success"))
