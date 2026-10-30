import streamlit as st
from utils.ui_components import render_sidebar, render_footer, load_custom_css
from database import get_quiz_attempts_for_user, get_topic_by_id
from recommendation_engine import generate_adaptive_guidance, get_topic_analytics
from ai_service import explain_topic
from utils.helpers import get_performance_tier

st.set_page_config(page_title="AI Feedback & Recommendations • AI Learning Coach", page_icon="🎯", layout="wide")
render_sidebar()
load_custom_css()

st.title("🎯 AI Performance Feedback & Adaptive Recommendations")
st.markdown("Pedagogical analysis and adaptive coaching based on your actual assessment history.")

user_id = st.session_state.current_user_id
attempts = get_quiz_attempts_for_user(user_id)

if not attempts:
    st.info("⚠️ No quiz attempts recorded yet. Take a quiz first to receive personalized AI coaching.")
    if st.button("📝 Go to Practice Quiz", type="primary"):
        st.switch_page("pages/3_Practice_Quiz.py")
    st.stop()

# Select which attempt to view analysis for
attempt_labels = {
    att["id"]: f"Attempt #{att['id']} — {att['topic_name']} ({att['score_percentage']}%) on {att['submitted_at'][:19]}"
    for att in attempts
}
latest_attempt_id = attempts[0]["id"]
selected_attempt_id = st.selectbox(
    "Select Assessment Attempt for Deep Analysis",
    options=list(attempt_labels.keys()),
    format_func=lambda x: attempt_labels[x],
    index=0,
    key="feedback_attempt_selector",
)

current_attempt = next(a for a in attempts if a["id"] == selected_attempt_id)
topic_id = current_attempt["topic_id"]
topic_name = current_attempt["topic_name"]
score_pct = current_attempt["score_percentage"]
correct = current_attempt["correct_answers"]
total = current_attempt["total_questions"]
tier = get_performance_tier(score_pct)

# Check if pre-cached guidance exists in session
cached_guidance = st.session_state.get("last_guidance")
if cached_guidance and cached_guidance.get("topic_id") == topic_id and cached_guidance.get("score_percentage") == score_pct:
    guidance = cached_guidance
else:
    with st.spinner("🧠 AI is analyzing your answers and tailoring recommendations..."):
        guidance = generate_adaptive_guidance(
            user_id=user_id,
            topic_id=topic_id,
            score_percentage=score_pct,
            correct_answers=correct,
            total_questions=total,
            topic_name=topic_name,
        )

eval_data = guidance.get("evaluation", {})
rec_data = guidance.get("recommendations", {})

# Performance Overview Card
st.markdown(
    f"""
    <div style="background: white; border: 1px solid #e2e8f0; border-left: 6px solid {tier['color']}; border-radius: 14px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.02);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-weight: 700; color: #64748b; text-transform: uppercase; font-size: 0.85rem;">Topic: {topic_name}</span>
            <span class="badge" style="background: {tier['color']}22; color: {tier['color']}; font-size: 0.85rem;">{tier['badge']}</span>
        </div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #1e293b; margin-bottom: 0.5rem;">
            {score_pct}% Score ({correct}/{total} Correct)
        </div>
        <p style="color: #475569; font-size: 1.05rem; line-height: 1.6; margin: 0;">
            {eval_data.get('summary_feedback', tier['summary'])}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Pedagogical Analysis: Strengths vs Weak Concepts
col_str, col_weak = st.columns(2)
with col_str:
    st.markdown("### 🟢 Concepts Understood")
    strengths = eval_data.get("strengths", ["Demonstrated effort in tackling assessment"])
    if strengths:
        for s in strengths:
            st.markdown(f"✅ {s}")
    else:
        st.write("Keep practicing to build consistent conceptual clarity.")

with col_weak:
    st.markdown("### 🔴 Needs Attention / Revision")
    weak_areas = eval_data.get("weak_areas", [])
    if weak_areas:
        for w in weak_areas:
            st.markdown(f"⚠️ {w}")
    else:
        st.markdown("🎉 No critical conceptual gaps detected on this assessment!")

st.markdown("<br><hr><br>", unsafe_allow_html=True)

# Adaptive Recommendation Card
rec_type = rec_data.get("recommendation_type", "practice")
rec_headline = rec_data.get("recommendation_headline", "Recommended Next Step")
detailed_advice = rec_data.get("detailed_advice", "")
next_step = rec_data.get("recommended_next_step", "")
mini_proj = rec_data.get("mini_project_or_challenge", "")

st.markdown(
    f"""
    <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(168, 85, 247, 0.05)); border: 1px solid #cbd5e1; border-radius: 14px; padding: 1.75rem; margin-bottom: 1.5rem;">
        <div style="font-size: 0.85rem; font-weight: 700; color: #4338ca; text-transform: uppercase; margin-bottom: 0.5rem;">
            🧭 ADAPTIVE LEARNING ENGINE RECOMMENDATION ({rec_type.upper()})
        </div>
        <h3 style="font-size: 1.4rem; color: #1e293b; margin: 0 0 0.75rem 0;">{rec_headline}</h3>
        <p style="color: #334155; font-size: 1rem; line-height: 1.6; margin-bottom: 1rem;">
            {detailed_advice}
        </p>
        <div style="background: white; border-radius: 10px; padding: 1rem; border: 1px solid #e2e8f0; margin-bottom: 0.75rem;">
            <strong>🎯 Direct Action:</strong> {next_step}
        </div>
        {f'<div style="background: #f8fafc; border-radius: 10px; padding: 1rem; border: 1px dashed #94a3b8;"><strong>💡 Hands-on Challenge:</strong> {mini_proj}</div>' if mini_proj else ''}
    </div>
    """,
    unsafe_allow_html=True,
)

# On-Demand Deep Explanation Section
st.markdown("### 📖 On-Demand AI Topic Study Guide")
st.markdown(f"Need a deeper conceptual breakdown of **{topic_name}**? Generate a full study guide with code analogies below.")

explain_col1, explain_col2 = st.columns([1.5, 3])
with explain_col1:
    gen_exp_btn = st.button("Generate Full Study Guide", type="primary", key="btn_gen_study_guide")

if gen_exp_btn or "cached_explanation" in st.session_state:
    if gen_exp_btn:
        with st.spinner("🤖 Gemini is writing your comprehensive tutorial guide..."):
            guide = explain_topic(topic_name=topic_name, level="Beginner")
            st.session_state.cached_explanation = guide

    st.markdown(st.session_state.cached_explanation)

render_footer()
