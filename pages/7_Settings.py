import os
import streamlit as st
from utils.ui_components import render_sidebar, render_footer, load_custom_css
from utils.config import (
    get_gemini_api_key,
    save_gemini_api_key,
    DATABASE_PATH,
    DEFAULT_GEMINI_MODEL,
    SCORE_THRESHOLD_REVISION,
    SCORE_THRESHOLD_PRACTICE,
    SCORE_THRESHOLD_PROGRESS,
)
from database import get_connection, init_db

st.set_page_config(page_title="Settings • AI Learning Coach", page_icon="⚙️", layout="wide")
render_sidebar()
load_custom_css()

st.title("⚙️ System Settings & API Configuration")
st.markdown("Configure your Google Gemini credentials, database parameters, and coaching thresholds.")

col_api, col_info = st.columns([1.5, 1])

with col_api:
    st.markdown("### 🔑 Google Gemini API Configuration")
    st.markdown(
        "Enter your Google AI Studio API key. Keys are safely stored in your local `.env` and never logged or committed."
    )

    current_key = get_gemini_api_key()
    masked_key = f"{current_key[:4]}...{current_key[-4:]}" if len(current_key) > 8 else ("Configured" if current_key else "Not Set")

    st.write(f"**Current Status:** {'🟢 Active' if current_key else '🟡 Missing (Running in Dynamic Fallback Mode)'}")
    
    with st.form("api_key_form"):
        api_input = st.text_input(
            "Gemini API Key",
            value=current_key,
            type="password",
            placeholder="AIzaSy...",
            help="Get your free API key at https://aistudio.google.com/",
        )
        model_selection = st.selectbox(
            "Default Gemini Model",
            options=["gemini-2.5-flash", "gemini-1.5-flash"],
            index=0,
            help="Ultra-fast, structured-output capable model for study plans and quizzes.",
        )
        save_api_btn = st.form_submit_button("💾 Save Credentials", type="primary", use_container_width=True)

    if save_api_btn:
        save_gemini_api_key(api_input)
        st.success("✅ Credentials safely updated in local `.env`!")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Configurable Performance Thresholds")
    st.markdown(
        f"""
        - **Below {SCORE_THRESHOLD_REVISION}%:** Low Performance — Recommends core revision, simpler breakdown, and practice quiz.
        - **{SCORE_THRESHOLD_REVISION}% – {SCORE_THRESHOLD_PRACTICE}%:** Medium-Low — Recommends more practice and mistake review.
        - **{SCORE_THRESHOLD_PRACTICE}% – {SCORE_THRESHOLD_PROGRESS}%:** Medium-High — Good understanding, consolidated learning.
        - **{SCORE_THRESHOLD_PROGRESS}% and above:** High Performance — Ready to progress, advanced questions, mini-project.
        """
    )

with col_info:
    st.markdown("### 🗄️ SQLite Database Status")
    st.write(f"**Path:** `{DATABASE_PATH}`")

    try:
        conn = get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r["name"] for r in cursor.fetchall() if not r["name"].startswith("sqlite_")]
        st.write(f"**Initialized Tables:** `{', '.join(tables)}`")

        counts = {}
        for t in tables:
            c = conn.execute(f"SELECT COUNT(*) as count FROM {t}").fetchone()["count"]
            counts[t] = c
        conn.close()

        st.markdown("**Row Counts:**")
        for tbl, cnt in counts.items():
            st.markdown(f"- `{tbl}`: **{cnt}** rows")

    except Exception as e:
        st.error(f"Database inspection error: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🔄 Maintenance Actions")
    if st.button("Initialize / Repair Database"):
        init_db()
        st.success("Database schema verified and initialized.")

render_footer()
