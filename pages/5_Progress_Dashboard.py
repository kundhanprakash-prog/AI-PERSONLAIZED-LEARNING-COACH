import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.ui_components import render_sidebar, render_footer, load_custom_css
from analytics import get_dashboard_metrics
from utils.helpers import get_performance_tier, format_timestamp

st.set_page_config(page_title="Progress Dashboard • AI Learning Coach", page_icon="📊", layout="wide")
render_sidebar()
load_custom_css()

st.title("📊 Learning Analytics & Progress Dashboard")
st.markdown("Live analytics and continuous performance telemetry queried directly from your SQLite database.")

user_id = st.session_state.current_user_id
user_name = st.session_state.current_user_name

metrics = get_dashboard_metrics(user_id)

# 1. Top KPI Cards
st.markdown("### 📈 Core Telemetry")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

kpi1.metric("Study Plans", metrics["total_plans"])
kpi2.metric("Topics Completed", f"{metrics['completed_topics']} / {metrics['total_topics']}")
kpi3.metric("Completion Rate", f"{metrics['completion_percentage']}%")
kpi4.metric("Quizzes Taken", metrics["total_quizzes"])
kpi5.metric("Average Score", f"{metrics['average_quiz_score']}%", delta=f"Best: {metrics['best_quiz_score']}%")

# Recommended Next Action Banner
st.markdown(
    f"""
    <div style="background: white; border: 1px solid #e2e8f0; border-left: 5px solid #4f46e5; border-radius: 12px; padding: 1.25rem 1.5rem; margin: 1.5rem 0; box-shadow: 0 2px 6px rgba(0,0,0,0.02);">
        <div style="font-size: 0.8rem; font-weight: 700; color: #4f46e5; text-transform: uppercase;">Recommended Next Milestone</div>
        <div style="font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-top: 0.25rem;">
            🎯 {metrics['recommended_next_action']}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 2. Charts Section
st.markdown("### 📊 Performance Visualizations")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 📈 Score Trend Over Time")
    trend = metrics["score_trend"]
    if trend and len(trend) > 0:
        df_trend = pd.DataFrame(trend)
        df_trend["Attempt"] = range(1, len(df_trend) + 1)
        fig_trend = px.line(
            df_trend,
            x="Attempt",
            y="score_percentage",
            markers=True,
            hover_data=["topic_name", "submitted_at"],
            labels={"score_percentage": "Score (%)", "Attempt": "Quiz Attempt #"},
            title="Quiz Score Progression",
        )
        fig_trend.update_traces(line_color="#4f46e5", line_width=3, marker_size=8)
        fig_trend.add_hline(y=70, line_dash="dash", line_color="#10b981", annotation_text="Target Understanding (70%)")
        fig_trend.update_layout(yaxis_range=[0, 105], margin=dict(l=20, r=20, t=40, b=20), height=320)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Complete at least one quiz to plot your score trajectory.")

with col_chart2:
    st.markdown("#### 🍩 Curriculum Progress Breakdown")
    completed = metrics["completed_topics"]
    pending = metrics["pending_topics"]
    if completed + pending > 0:
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=["Completed Topics", "Pending Topics"],
                    values=[completed, pending],
                    hole=0.6,
                    marker=dict(colors=["#10b981", "#e2e8f0"]),
                )
            ]
        )
        fig_pie.update_layout(
            annotations=[dict(text=f"{metrics['completion_percentage']}%", x=0.5, y=0.5, font_size=24, showarrow=False)],
            margin=dict(l=20, r=20, t=40, b=20),
            height=320,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Create a study plan to visualize curriculum progress.")

st.markdown("<br>", unsafe_allow_html=True)

# 3. Topic Strengths vs Weaknesses
st.markdown("### 🔍 Topic Knowledge Profile")
col_weak, col_strong = st.columns(2)

with col_weak:
    st.markdown("#### 🔴 Topics Requiring Revision (<70%)")
    weak = metrics["weak_topics"]
    if weak:
        for w in weak:
            st.markdown(
                f"""
                <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: #991b1b;">{w['topic_name']}</span>
                    <span class="badge badge-danger">{w['average_score']}% Avg ({w['attempts']} attempts)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("No critical weak topics identified. Solid performance across attempted topics!")

with col_strong:
    st.markdown("#### 🟢 Strong Topics (≥85%)")
    strong = metrics["strong_topics"]
    if strong:
        for s in strong:
            st.markdown(
                f"""
                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: #166534;">{s['topic_name']}</span>
                    <span class="badge badge-success">{s['average_score']}% Avg ({s['attempts']} attempts)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Score 85% or higher on assessments to catalog strong topic proficiencies.")

st.markdown("<br>", unsafe_allow_html=True)

# 4. Recent Recommendations
st.markdown("### 📋 Recent Adaptive AI Guidance")
recent_recs = metrics["recent_recommendations"]
if recent_recs:
    for r in recent_recs:
        st.markdown(
            f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span style="font-weight: 700; color: #4338ca;">{r.get('topic_name') or 'General Curriculum'}</span>
                    <span class="badge badge-primary">{r.get('recommendation_type', '').upper()}</span>
                </div>
                <div style="color: #475569; font-size: 0.92rem;">{r.get('recommendation')}</div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.5rem;">{r.get('created_at')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.info("No recorded recommendations yet.")

render_footer()
