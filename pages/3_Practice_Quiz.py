import streamlit as st
from utils.ui_components import render_sidebar, render_footer, load_custom_css
from database import get_plan_topics, get_topic_by_id, get_user_study_plans
from quiz_manager import fetch_topic_quiz, evaluate_and_record_quiz, get_topic_quiz_history
from recommendation_engine import generate_adaptive_guidance

st.set_page_config(page_title="Practice Quiz • AI Learning Coach", page_icon="📝", layout="wide")
render_sidebar()
load_custom_css()

st.title("📝 Interactive Topic Assessment")
st.markdown("Test your subject mastery through dynamically generated multiple-choice questions.")

user_id = st.session_state.current_user_id
user_name = st.session_state.current_user_name
active_plan_id = st.session_state.get("active_plan_id")

# Fetch available topics for selection
user_plans = get_user_study_plans(user_id)
all_topics = []
for p in user_plans:
    topics = get_plan_topics(p["id"])
    for t in topics:
        t["plan_subject"] = p["subject"]
        all_topics.append(t)

if not all_topics:
    st.warning("⚠️ No topics found in your learning plans. Please create a study plan first.")
    if st.button("📅 Go to Study Plan Page", type="primary"):
        st.switch_page("pages/2_Study_Plan.py")
    st.stop()

# Topic selector dropdown
topic_options = {t["id"]: f"Day {t['day_number']}: {t['topic_name']} ({t['plan_subject']})" for t in all_topics}
curr_topic_id = st.session_state.get("active_topic_id")
if curr_topic_id not in topic_options:
    curr_topic_id = all_topics[0]["id"]
    st.session_state.active_topic_id = curr_topic_id

selected_topic_id = st.selectbox(
    "Select Study Topic for Assessment",
    options=list(topic_options.keys()),
    format_func=lambda x: topic_options[x],
    index=list(topic_options.keys()).index(curr_topic_id),
    key="quiz_topic_selector",
)

if selected_topic_id != st.session_state.get("active_topic_id"):
    st.session_state.active_topic_id = selected_topic_id
    st.session_state.pop("current_quiz_questions", None)
    st.session_state.pop("quiz_submitted_result", None)
    st.session_state.pop("quiz_user_answers", None)
    st.rerun()

topic_info = get_topic_by_id(selected_topic_id)
topic_name = topic_info["topic_name"] if topic_info else "Selected Topic"

# Display past attempts for this topic
past_attempts = get_topic_quiz_history(user_id, selected_topic_id)
if past_attempts:
    with st.expander(f"📜 View Past Attempts on this Topic ({len(past_attempts)} total)"):
        for att in past_attempts:
            st.markdown(
                f"• Attempt #{att['id']} — **{att['score_percentage']}%** ({att['correct_answers']}/{att['total_questions']}) on `{att['submitted_at'][:19]}`"
            )

# Check if questions exist in session state or need generation
if "current_quiz_questions" not in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info(f"Ready to test your knowledge on **{topic_name}**? Click below to generate 5 dynamic questions.")
    if st.button("🚀 Generate 5 MCQs (Gemini AI)", type="primary"):
        with st.spinner("🤖 Gemini is designing your custom assessment..."):
            success, questions, msg = fetch_topic_quiz(
                topic_name=topic_name,
                level="Beginner",
                count=5,
            )
            if success and questions:
                st.session_state.current_quiz_questions = questions
                st.session_state.quiz_submitted_result = None
                st.session_state.quiz_user_answers = {}
                st.session_state.confirm_submission = False
                st.rerun()
            else:
                st.error(f"Failed to generate quiz: {msg}")
    st.stop()

# If quiz questions are active
questions = st.session_state.current_quiz_questions
submitted_result = st.session_state.get("quiz_submitted_result")

if submitted_result is None:
    # Quiz taking interface
    st.markdown(f"### Questions for: `{topic_name}`")
    st.caption("Select the best answer for each question. Scoring is computed directly in Python.")

    if "quiz_user_answers" not in st.session_state:
        st.session_state.quiz_user_answers = {}

    # Render questions
    for idx, q in enumerate(questions):
        st.markdown(
            f"""
            <div class="quiz-question-box">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <span style="font-weight: 700; color: #4338ca; font-size: 0.95rem;">Question {idx + 1} of {len(questions)}</span>
                    <span class="badge" style="background: #f1f5f9; color: #475569;">{q.get('difficulty', 'Medium')}</span>
                </div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #1e293b; margin-bottom: 1rem;">
                    {q.get('question_text')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        options = q.get("options", [])
        current_ans = st.session_state.quiz_user_answers.get(idx)
        opt_index = options.index(current_ans) if current_ans in options else None

        choice = st.radio(
            label=f"Options for Question {idx + 1}",
            options=options,
            index=opt_index,
            key=f"radio_q_{idx}",
            label_visibility="collapsed",
        )
        if choice:
            st.session_state.quiz_user_answers[idx] = choice

        st.markdown("<br>", unsafe_allow_html=True)

    # Submission section
    answered_count = len([a for a in st.session_state.quiz_user_answers.values() if a])
    st.write(f"📊 Answered: **{answered_count} of {len(questions)}** questions")
    st.progress(answered_count / len(questions))

    col_sub1, col_sub2 = st.columns([1.5, 3])
    with col_sub1:
        confirm = st.checkbox("I confirm these are my final answers", key="chk_confirm_sub")
        submit_btn = st.button("📥 Submit Quiz", type="primary", disabled=not confirm, use_container_width=True)

    if submit_btn:
        with st.spinner("⚖️ Scoring answers with Python logic and logging attempt in SQLite..."):
            result = evaluate_and_record_quiz(
                user_id=user_id,
                topic_id=selected_topic_id,
                questions=questions,
                user_answers=st.session_state.quiz_user_answers,
            )
            st.session_state.quiz_submitted_result = result

            # Generate adaptive feedback in background
            guidance = generate_adaptive_guidance(
                user_id=user_id,
                topic_id=selected_topic_id,
                score_percentage=result["score_percentage"],
                correct_answers=result["correct_answers"],
                total_questions=result["total_questions"],
                topic_name=topic_name,
                level="Beginner",
                incorrect_questions=result["incorrect_questions"],
            )
            st.session_state.last_guidance = guidance
            st.rerun()

else:
    # Quiz Results Screen
    res = submitted_result
    st.balloons()
    st.markdown("## 🎯 Assessment Results")
    
    tier = res["performance_tier"]
    score_pct = res["score_percentage"]
    correct = res["correct_answers"]
    total = res["total_questions"]

    # Score banner
    st.markdown(
        f"""
        <div style="background: white; border: 2px solid {tier['color']}; border-radius: 16px; padding: 2rem; text-align: center; margin-bottom: 2rem; box-shadow: 0 4px 16px rgba(0,0,0,0.04);">
            <div style="font-size: 1.1rem; color: #64748b; font-weight: 600;">Overall Quiz Score</div>
            <div style="font-size: 3.5rem; font-weight: 800; font-family: 'Outfit'; color: {tier['color']}; margin: 0.5rem 0;">
                {score_pct}%
            </div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem;">
                {correct} out of {total} Questions Correct
            </div>
            <div>
                <span class="badge" style="background: {tier['color']}22; color: {tier['color']}; font-size: 0.9rem; padding: 0.4rem 1rem;">
                    {tier['badge']} • {tier['label']}
                </span>
            </div>
            <p style="color: #475569; max-width: 600px; margin: 1rem auto 0 auto; font-size: 0.95rem;">
                {tier['summary']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed Question-by-Question Review
    st.markdown("### 📋 Detailed Answers & Explanations")
    for resp in res["responses"]:
        is_c = resp["is_correct"]
        box_color = "#10b981" if is_c else "#ef4444"
        bg_color = "#f0fdf4" if is_c else "#fef2f2"
        status_text = "✅ Correct" if is_c else "❌ Incorrect"

        with st.container():
            st.markdown(
                f"""
                <div style="background: {bg_color}; border: 1px solid {box_color}55; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="font-weight: 700; color: #1e293b;">Question {resp['question_index']}</span>
                        <span style="font-weight: 700; color: {box_color};">{status_text}</span>
                    </div>
                    <div style="font-size: 1.05rem; font-weight: 600; color: #1e293b; margin-bottom: 0.75rem;">
                        {resp['question_text']}
                    </div>
                    <div style="font-size: 0.92rem; margin-bottom: 0.25rem;">
                        <strong>Your Answer:</strong> <span style="color: {'#15803d' if is_c else '#b91c1c'};">{resp['selected_answer']}</span>
                    </div>
                    <div style="font-size: 0.92rem; margin-bottom: 0.75rem;">
                        <strong>Correct Answer:</strong> <span style="color: #15803d; font-weight: 600;">{resp['correct_answer']}</span>
                    </div>
                    <div style="background: white; border-radius: 8px; padding: 0.75rem 1rem; border: 1px solid #e2e8f0; font-size: 0.88rem; color: #334155;">
                        💡 <strong>Explanation:</strong> {resp['explanation']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Navigation Actions
    col_act1, col_act2, col_act3 = st.columns([1.5, 1.5, 2])
    with col_act1:
        if st.button("🤖 View AI Coaching & Next Steps", type="primary", use_container_width=True):
            st.switch_page("pages/4_AI_Feedback.py")
    with col_act2:
        if st.button("🔄 Retake Practice Quiz", use_container_width=True):
            st.session_state.pop("current_quiz_questions", None)
            st.session_state.pop("quiz_submitted_result", None)
            st.session_state.pop("quiz_user_answers", None)
            st.rerun()
    with col_act3:
        if st.button("📅 Back to Study Plan", use_container_width=True):
            st.switch_page("pages/2_Study_Plan.py")

render_footer()
