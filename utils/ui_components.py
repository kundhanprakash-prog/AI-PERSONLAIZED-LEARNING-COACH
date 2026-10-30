import streamlit as st
from pathlib import Path
from database import list_all_users, get_or_create_user, init_db

def load_custom_css():
    """Inject custom SaaS styles into Streamlit page."""
    css_path = Path(__file__).resolve().parent.parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def init_session_state():
    """Ensure essential state variables are initialized."""
    init_db()
    if "current_user_id" not in st.session_state:
        # Check if users exist in DB
        users = list_all_users()
        if users:
            st.session_state.current_user_id = users[0]["id"]
            st.session_state.current_user_name = users[0]["name"]
        else:
            # Default demo learner
            uid = get_or_create_user("Alex Johnson")
            st.session_state.current_user_id = uid
            st.session_state.current_user_name = "Alex Johnson"

    if "active_plan_id" not in st.session_state:
        st.session_state.active_plan_id = None

    if "active_topic_id" not in st.session_state:
        st.session_state.active_topic_id = None

    if "quiz_in_progress" not in st.session_state:
        st.session_state.quiz_in_progress = False

def render_sidebar():
    """Render common sidebar user selector, branding, and quick stats."""
    init_session_state()
    load_custom_css()

    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1.25rem;">
                <div style="background: linear-gradient(135deg, #4f46e5, #9333ea); width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold;">
                    ⚡
                </div>
                <div>
                    <div style="font-weight: 800; font-size: 1.05rem; color: #1e293b; line-height: 1.1;">AI Study Coach</div>
                    <div style="font-size: 0.72rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Xpert Champs</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.subheader("👤 Active Student")
        users = list_all_users()
        user_names = [u["name"] for u in users]
        current_name = st.session_state.get("current_user_name", "Alex Johnson")

        idx = user_names.index(current_name) if current_name in user_names else 0
        selected_user = st.selectbox("Select Student Profile", options=user_names, index=idx, key="sidebar_user_select")
        
        # If user changed
        selected_user_obj = next((u for u in users if u["name"] == selected_user), None)
        if selected_user_obj and selected_user_obj["id"] != st.session_state.current_user_id:
            st.session_state.current_user_id = selected_user_obj["id"]
            st.session_state.current_user_name = selected_user_obj["name"]
            st.session_state.active_plan_id = None
            st.session_state.active_topic_id = None
            st.rerun()

        # Add new student quick trigger
        with st.expander("➕ Switch or Add Student"):
            new_name = st.text_input("New Student Name", placeholder="e.g. Maya Chen", key="sidebar_new_student")
            if st.button("Create & Switch", key="btn_create_student"):
                if new_name and len(new_name.strip()) >= 2:
                    new_uid = get_or_create_user(new_name.strip())
                    st.session_state.current_user_id = new_uid
                    st.session_state.current_user_name = new_name.strip()
                    st.session_state.active_plan_id = None
                    st.success(f"Switched to {new_name.strip()}!")
                    st.rerun()
                else:
                    st.error("Name must be at least 2 characters.")

        st.markdown("---")
        st.caption("✨ Powered by Google Gemini & SQLite")
        st.caption("Version 1.0.0 • Production Ready")

def render_footer():
    """Render unified SaaS footer."""
    st.markdown(
        """
        <div class="app-footer">
            <p><strong>AI Personalized Learning Coach</strong> — Built for <strong>Xpert Champs</strong></p>
            <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem;">
                Generative AI • Adaptive Quizzes • Weak-Topic Detection • Continuous Mastery Tracking
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
