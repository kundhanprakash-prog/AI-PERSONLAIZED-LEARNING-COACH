import streamlit as st
import json
from utils.ui_components import render_sidebar, render_footer, load_custom_css
from database import (
    get_latest_profile,
    get_user_study_plans,
    get_study_plan,
    get_plan_topics,
    update_topic_status,
)
from learning_plan import create_and_save_study_plan, get_plan_summary, mark_topic_completed, mark_topic_pending
from ai_service import explain_topic

st.set_page_config(page_title="My Study Plan • AI Learning Coach", page_icon="📅", layout="wide")
render_sidebar()
load_custom_css()

st.title("📅 Personalized Study Plan Dashboard")
st.markdown("Track your day-by-day learning schedule, mark completed milestones, and take topic quizzes.")

user_id = st.session_state.current_user_id
user_name = st.session_state.current_user_name
latest_profile = get_latest_profile(user_id)

# Fetch user's existing plans from SQLite
user_plans = get_user_study_plans(user_id)

# Action bar: Generate Plan or Select Plan
col_sel, col_act = st.columns([2, 1.2])

with col_sel:
    if user_plans:
        plan_options = {p["id"]: f"Plan #{p['id']} - {p['subject']} ({p['created_at'][:10]})" for p in user_plans}
        current_plan_id = st.session_state.get("active_plan_id")
        if current_plan_id not in plan_options:
            current_plan_id = user_plans[0]["id"]
            st.session_state.active_plan_id = current_plan_id

        selected_plan_id = st.selectbox(
            "Select Active Study Plan",
            options=list(plan_options.keys()),
            format_func=lambda x: plan_options[x],
            index=list(plan_options.keys()).index(current_plan_id),
            key="plan_dropdown_select",
        )
        if selected_plan_id != st.session_state.active_plan_id:
            st.session_state.active_plan_id = selected_plan_id
            st.rerun()
    else:
        st.info("No study plan generated yet for this student. Click 'Generate New Study Plan' to create one.")

with col_act:
    st.write("") # vertical spacing
    st.write("")
    if st.button("✨ Generate New Plan (Gemini AI)", type="primary", use_container_width=True):
        if not latest_profile:
            st.warning("Please complete your Student Profile setup first.")
            st.switch_page("pages/1_Student_Profile.py")
        else:
            with st.spinner("🧠 Gemini is generating your personalized day-by-day curriculum..."):
                approach = st.session_state.get("selected_approach", "Balanced")
                success, new_plan_id, plan_dict, msg = create_and_save_study_plan(
                    user_id=user_id,
                    subject=latest_profile["subject"],
                    learning_goal=latest_profile["learning_goal"],
                    current_level=latest_profile["current_level"],
                    target_duration=latest_profile["target_duration"],
                    daily_study_time=latest_profile["daily_study_time"],
                    approach=approach,
                    user_name=user_name,
                )
                if success:
                    st.session_state.active_plan_id = new_plan_id
                    st.success("🎉 New personalized study plan generated successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to generate plan: {msg}")

# Display Active Plan Dashboard
active_plan_id = st.session_state.get("active_plan_id")

if active_plan_id:
    summary = get_plan_summary(active_plan_id)
    if summary:
        # Header Statistics Cards
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Subject", summary["subject"])
        m2.metric("Total Days", f"{summary['total_days']} Days")
        m3.metric("Completed Topics", f"{summary['completed_topics']} / {summary['total_topics']}")
        m4.metric("Pending Topics", summary["pending_topics"])
        m5.metric("Progress", f"{summary['completion_percentage']}%")

        # Visual Progress Bar
        st.progress(summary["completion_percentage"] / 100.0)

        # Plan Goal
        st.info(f"🎯 **Goal:** {summary['learning_goal']}")

        st.markdown("### 📚 Daily Curriculum & Topic Milestones")
        topics = summary["topics"]
        plan_days = summary["plan_data"].get("days", [])

        # Map day details from plan_data
        day_details_map = {d.get("day_number"): d for d in plan_days}

        for topic in topics:
            t_id = topic["id"]
            day_num = topic["day_number"]
            t_name = topic["topic_name"]
            status = topic["status"]
            est_time = topic["estimated_time"]
            is_completed = (status == "completed")

            day_detail = day_details_map.get(day_num, {})
            subtopics = day_detail.get("subtopics", [])
            activities = day_detail.get("practice_activities", [])
            resources = day_detail.get("resources", [])

            card_border = "#10b981" if is_completed else "#6366f1"
            card_bg = "#f0fdf4" if is_completed else "#ffffff"
            badge_html = (
                '<span class="badge badge-success">✅ Completed</span>'
                if is_completed
                else '<span class="badge badge-primary">⏳ Pending</span>'
            )

            with st.container():
                st.markdown(
                    f"""
                    <div style="background: {card_bg}; border: 1px solid #e2e8f0; border-left: 6px solid {card_border}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span style="font-weight: 800; font-size: 0.85rem; color: #64748b; text-transform: uppercase;">DAY {day_num}</span>
                            <div>{badge_html} <span class="badge" style="background: #f1f5f9; color: #475569; margin-left: 6px;">⏱️ {est_time} min</span></div>
                        </div>
                        <h3 style="font-size: 1.25rem; margin: 0 0 0.5rem 0; color: #1e293b;">{t_name}</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Expandable details
                with st.expander(f"🔍 View Day {day_num} Details, Subtopics & Activities"):
                    c_det1, c_det2 = st.columns([1.5, 1])
                    with c_det1:
                        if topic.get("objectives_list"):
                            st.markdown("**Learning Objectives:**")
                            for obj in topic["objectives_list"]:
                                st.markdown(f"- {obj}")

                        if subtopics:
                            st.markdown("**Key Subtopics:**")
                            for sub in subtopics:
                                st.markdown(f"• `{sub}`")

                    with c_det2:
                        if activities:
                            st.markdown("**Practice Activities:**")
                            for act in activities:
                                st.markdown(f"🔨 {act}")

                        if resources:
                            st.markdown("**Recommended Resources:**")
                            for res in resources:
                                st.markdown(f"📖 {res}")

                # Action buttons row
                btn_c1, btn_c2, btn_c3 = st.columns([1.5, 1.5, 3])
                with btn_c1:
                    if is_completed:
                        if st.button("↩️ Mark as Pending", key=f"btn_pending_{t_id}"):
                            mark_topic_pending(t_id)
                            st.rerun()
                    else:
                        if st.button("✅ Mark as Completed", type="primary", key=f"btn_complete_{t_id}"):
                            mark_topic_completed(t_id)
                            st.rerun()

                with btn_c2:
                    if st.button("🧠 Practice Quiz", key=f"btn_quiz_{t_id}"):
                        st.session_state.active_topic_id = t_id
                        st.session_state.active_topic_name = t_name
                        st.switch_page("pages/3_Practice_Quiz.py")

                with btn_c3:
                    if st.button("📖 Read AI Explanation", key=f"btn_explain_{t_id}"):
                        st.session_state.explain_topic_name = t_name
                        st.session_state.explain_topic_subtopics = subtopics
                        st.session_state.explain_topic_level = summary.get("plan_data", {}).get("level", "Beginner")
                        st.switch_page("pages/4_AI_Feedback.py")

                st.markdown("<br>", unsafe_allow_html=True)
else:
    st.info("Please select or generate a study plan to view the dashboard.")

render_footer()
