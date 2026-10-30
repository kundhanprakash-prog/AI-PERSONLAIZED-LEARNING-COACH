import streamlit as st
from utils.ui_components import render_sidebar, render_footer, load_custom_css
from utils.config import KNOWLEDGE_LEVELS, LEARNING_APPROACHES
from database import get_or_create_user, save_learner_profile, get_latest_profile, get_user_by_id
from validators import validate_learner_profile

st.set_page_config(page_title="Student Profile • AI Learning Coach", page_icon="👤", layout="wide")
render_sidebar()
load_custom_css()

st.title("👤 Student Profile & Learning Setup")
st.markdown("Set up your learning profile to let Gemini tailor custom daily study schedules to your pace.")

user_id = st.session_state.current_user_id
current_user = get_user_by_id(user_id)
user_name = current_user["name"] if current_user else "Learner"

# Fetch existing profile if available
existing_profile = get_latest_profile(user_id)

col_form, col_summary = st.columns([1.6, 1.1])

with col_form:
    st.markdown("### 📝 Learning Goal & Profile Form")
    with st.form("profile_setup_form"):
        name_input = st.text_input("Full Name", value=user_name, help="Your full display name")
        
        col_subj, col_level = st.columns(2)
        with col_subj:
            subject_default = existing_profile["subject"] if existing_profile else "Python Programming"
            subject_input = st.text_input(
                "Subject / Skill to Learn",
                value=subject_default,
                placeholder="e.g. Data Structures & Algorithms, Machine Learning",
                help="The core subject or skill you wish to master.",
            )
        with col_level:
            level_default = existing_profile["current_level"] if existing_profile else "Beginner"
            level_idx = KNOWLEDGE_LEVELS.index(level_default) if level_default in KNOWLEDGE_LEVELS else 0
            level_input = st.selectbox(
                "Current Knowledge Level",
                options=KNOWLEDGE_LEVELS,
                index=level_idx,
                help="Your current familiarity with the subject.",
            )

        goal_default = existing_profile["learning_goal"] if existing_profile else "Master fundamentals and build real-world portfolio projects"
        goal_input = st.text_area(
            "Target Learning Goal",
            value=goal_default,
            placeholder="e.g. Master backend API development with FastAPI and pass technical interviews",
            help="Describe what you want to achieve or build.",
            height=100,
        )

        col_dur, col_time = st.columns(2)
        with col_dur:
            dur_default = int(existing_profile["target_duration"]) if existing_profile else 7
            duration_input = st.number_input(
                "Target Duration (Days)",
                min_value=1,
                max_value=90,
                value=dur_default,
                step=1,
                help="How many total days you plan to allocate for this curriculum.",
            )
        with col_time:
            time_default = int(existing_profile["daily_study_time"]) if existing_profile else 45
            daily_time_input = st.number_input(
                "Daily Study Time (Minutes)",
                min_value=15,
                max_value=480,
                value=time_default,
                step=15,
                help="How many minutes you can dedicate each day.",
            )

        approach_input = st.selectbox(
            "Preferred Learning Approach (Optional)",
            options=LEARNING_APPROACHES,
            index=0,
            help="Choose how you prefer concepts to be structured.",
        )

        submit_btn = st.form_submit_button("💾 Save Profile & Continue", type="primary", use_container_width=True)

    if submit_btn:
        # Validate inputs
        is_valid, err_msg = validate_learner_profile(
            name=name_input,
            subject=subject_input,
            learning_goal=goal_input,
            current_level=level_input,
            target_duration=duration_input,
            daily_study_time=daily_time_input,
        )

        if not is_valid:
            st.error(f"⚠️ Validation Error: {err_msg}")
        else:
            # Update user if name changed
            if name_input.strip() != user_name:
                user_id = get_or_create_user(name_input.strip())
                st.session_state.current_user_id = user_id
                st.session_state.current_user_name = name_input.strip()

            # Save profile to SQLite
            profile_id = save_learner_profile(
                user_id=user_id,
                subject=subject_input,
                learning_goal=goal_input,
                current_level=level_input,
                target_duration=int(duration_input),
                daily_study_time=int(daily_time_input),
            )
            st.session_state["selected_approach"] = approach_input
            st.success("✅ Profile successfully saved in SQLite database!")
            st.info("You can now proceed to generate or review your personalized study plan.")

with col_summary:
    st.markdown("### 📌 Active Profile Summary")
    latest = get_latest_profile(user_id)
    if latest:
        st.markdown(
            f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                <div style="font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Learner</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #1e293b; margin-bottom: 0.75rem;">{st.session_state.current_user_name}</div>
                
                <div style="font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Subject</div>
                <div style="font-size: 1.05rem; font-weight: 600; color: #4338ca; margin-bottom: 0.75rem;">{latest['subject']}</div>
                
                <div style="font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Goal</div>
                <div style="font-size: 0.95rem; color: #334155; margin-bottom: 0.75rem;">{latest['learning_goal']}</div>
                
                <div style="display: flex; gap: 8px; margin-top: 1rem;">
                    <span class="badge badge-primary">Level: {latest['current_level']}</span>
                    <span class="badge badge-success">{latest['target_duration']} Days</span>
                    <span class="badge badge-warning">{latest['daily_study_time']} min/day</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📅 Proceed to Study Plan ➔", type="primary", use_container_width=True):
            st.switch_page("pages/2_Study_Plan.py")
    else:
        st.info("No saved profile yet. Complete the form on the left to initialize your learning profile.")

render_footer()
