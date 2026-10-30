import streamlit as st
from utils.ui_components import render_sidebar, render_footer, load_custom_css
from analytics import get_full_learning_history
from database import get_plan_topics, get_attempt_responses
from utils.helpers import get_performance_tier

st.set_page_config(page_title="Learning History • AI Learning Coach", page_icon="📜", layout="wide")
render_sidebar()
load_custom_css()

st.title("📜 Persistent Learning History")
st.markdown("Review all historical study plans, quiz scores, and AI recommendations saved across app sessions.")

user_id = st.session_state.current_user_id
history = get_full_learning_history(user_id)

tab_plans, tab_quizzes, tab_recs = st.tabs(["📅 Study Plans History", "📝 Quiz Attempts History", "💡 Recommendations Log"])

with tab_plans:
    plans = history.get("plans", [])
    if not plans:
        st.info("No study plans recorded yet. Create one to begin your history.")
    else:
        st.markdown(f"**Found {len(plans)} study plan(s):**")
        for plan in plans:
            p_id = plan["id"]
            p_subj = plan["subject"]
            p_goal = plan["learning_goal"]
            created = plan["created_at"]
            topics = get_plan_topics(p_id)
            completed_count = sum(1 for t in topics if t["status"] == "completed")
            total_count = len(topics)
            pct = round((completed_count / total_count * 100), 1) if total_count > 0 else 0

            with st.container():
                st.markdown(
                    f"""
                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span style="font-weight: 800; color: #4338ca; font-size: 1.1rem;">Plan #{p_id}: {p_subj}</span>
                            <span class="badge badge-primary">{created[:10]}</span>
                        </div>
                        <div style="color: #475569; font-size: 0.95rem; margin-bottom: 0.75rem;"><strong>Goal:</strong> {p_goal}</div>
                        <div style="display: flex; gap: 12px; margin-bottom: 0.75rem;">
                            <span class="badge badge-success">Completed: {completed_count}/{total_count} Topics</span>
                            <span class="badge" style="background: #f1f5f9; color: #334155;">Progress: {pct}%</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col_btn, _ = st.columns([2, 4])
                with col_btn:
                    if st.button(f"🚀 Reopen & Continue Plan #{p_id}", key=f"btn_reopen_{p_id}", type="primary"):
                        st.session_state.active_plan_id = p_id
                        st.switch_page("pages/2_Study_Plan.py")

with tab_quizzes:
    attempts = history.get("attempts", [])
    if not attempts:
        st.info("No quiz attempts recorded yet.")
    else:
        st.markdown(f"**Found {len(attempts)} quiz attempt(s):**")
        for att in attempts:
            a_id = att["id"]
            topic = att["topic_name"]
            score = att["score_percentage"]
            corr = att["correct_answers"]
            tot = att["total_questions"]
            date_str = att["submitted_at"]
            tier = get_performance_tier(score)

            with st.expander(f"Attempt #{a_id} — {topic} | {score}% ({corr}/{tot}) on {date_str[:19]}"):
                st.markdown(f"**Performance Tier:** {tier['badge']} ({tier['label']})")
                responses = get_attempt_responses(a_id)
                for r in responses:
                    icon = "✅" if r["is_correct"] else "❌"
                    st.markdown(
                        f"""
                        <div style="background: #f8fafc; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; font-size: 0.9rem;">
                            <div>{icon} <strong>{r['question_text']}</strong></div>
                            <div style="color: #475569; margin-top: 0.25rem;">Your Answer: <em>{r['selected_answer']}</em> | Correct: <strong>{r['correct_answer']}</strong></div>
                            <div style="color: #64748b; font-size: 0.82rem; margin-top: 0.25rem;">💡 {r['explanation']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

with tab_recs:
    recs = history.get("recommendations", [])
    if not recs:
        st.info("No recommendations logged yet.")
    else:
        st.markdown(f"**Found {len(recs)} recommendation(s):**")
        for r in recs:
            st.markdown(
                f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                        <span style="font-weight: 700; color: #4338ca;">{r.get('topic_name') or 'General Advice'}</span>
                        <span class="badge badge-primary">{r.get('recommendation_type', '').upper()}</span>
                    </div>
                    <div style="color: #334155; font-size: 0.92rem;">{r['recommendation']}</div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.5rem;">{r['created_at']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

render_footer()
