import logging
from typing import Dict, Any, List, Optional
from database import (
    get_connection,
    get_user_study_plans,
    get_quiz_attempts_for_user,
    get_user_recommendations,
)
from recommendation_engine import get_topic_analytics

logger = logging.getLogger(__name__)

def get_dashboard_metrics(user_id: int) -> Dict[str, Any]:
    """
    Compute real-time dashboard analytics from SQLite for a user.
    Never uses static or hardcoded metrics.
    """
    conn = get_connection()
    try:
        # 1. Total study plans
        cursor = conn.execute("SELECT COUNT(*) AS count FROM study_plans WHERE user_id = ?", (user_id,))
        total_plans = cursor.fetchone()["count"]

        # 2. Total, completed, and pending topics
        cursor = conn.execute(
            """
            SELECT 
                COUNT(*) AS total_topics,
                SUM(CASE WHEN st.status = 'completed' THEN 1 ELSE 0 END) AS completed_topics,
                SUM(CASE WHEN st.status != 'completed' THEN 1 ELSE 0 END) AS pending_topics
            FROM study_topics st
            JOIN study_plans sp ON st.plan_id = sp.id
            WHERE sp.user_id = ?
            """,
            (user_id,),
        )
        topic_stats = cursor.fetchone()
        total_topics = topic_stats["total_topics"] or 0
        completed_topics = topic_stats["completed_topics"] or 0
        pending_topics = topic_stats["pending_topics"] or 0
        completion_pct = round((completed_topics / total_topics * 100.0), 1) if total_topics > 0 else 0.0

        # 3. Quiz statistics
        cursor = conn.execute(
            """
            SELECT 
                COUNT(*) AS total_quizzes,
                AVG(score_percentage) AS avg_score,
                MAX(score_percentage) AS max_score,
                MIN(score_percentage) AS min_score
            FROM quiz_attempts
            WHERE user_id = ?
            """,
            (user_id,),
        )
        quiz_stats = cursor.fetchone()
        total_quizzes = quiz_stats["total_quizzes"] or 0
        avg_score = round(quiz_stats["avg_score"], 1) if quiz_stats["avg_score"] is not None else 0.0
        best_score = round(quiz_stats["max_score"], 1) if quiz_stats["max_score"] is not None else 0.0

        # 4. Score trends (historical attempts over time)
        cursor = conn.execute(
            """
            SELECT qa.id, qa.score_percentage, qa.submitted_at, st.topic_name
            FROM quiz_attempts qa
            JOIN study_topics st ON qa.topic_id = st.id
            WHERE qa.user_id = ?
            ORDER BY qa.submitted_at ASC
            """,
            (user_id,),
        )
        score_trend = [dict(r) for r in cursor.fetchall()]

        # 5. Topic breakdown (Weak and Strong topics)
        topic_analysis = get_topic_analytics(user_id)

        # 6. Recent learning recommendations
        recent_recommendations = get_user_recommendations(user_id=user_id, limit=5)

        # 7. Next action recommendation logic
        next_action = "Generate a personalized study plan to kickstart your journey."
        if total_plans > 0:
            if pending_topics > 0 and total_quizzes == 0:
                next_action = "Review your study plan and take your first topic practice quiz."
            elif topic_analysis["weak_topics"]:
                weakest = topic_analysis["weak_topics"][0]["topic_name"]
                next_action = f"Revise key concepts and re-take practice questions for '{weakest}'."
            elif pending_topics > 0:
                next_action = "Continue to the next pending study topic on your curriculum."
            else:
                next_action = "Congratulations! All planned topics completed. Generate a new advanced plan."

        return {
            "total_plans": total_plans,
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "pending_topics": pending_topics,
            "completion_percentage": completion_pct,
            "total_quizzes": total_quizzes,
            "average_quiz_score": avg_score,
            "best_quiz_score": best_score,
            "score_trend": score_trend,
            "weak_topics": topic_analysis["weak_topics"],
            "strong_topics": topic_analysis["strong_topics"],
            "moderate_topics": topic_analysis["moderate_topics"],
            "recent_recommendations": recent_recommendations,
            "recommended_next_action": next_action,
        }
    finally:
        conn.close()

def get_full_learning_history(user_id: int) -> Dict[str, Any]:
    """Retrieve full chronological learning history for a user."""
    conn = get_connection()
    try:
        # Study plans
        plans = get_user_study_plans(user_id)

        # Quiz attempts with topic & subject
        cursor = conn.execute(
            """
            SELECT qa.*, st.topic_name, st.day_number, sp.subject
            FROM quiz_attempts qa
            JOIN study_topics st ON qa.topic_id = st.id
            JOIN study_plans sp ON st.plan_id = sp.id
            WHERE qa.user_id = ?
            ORDER BY qa.submitted_at DESC
            """,
            (user_id,),
        )
        attempts = [dict(r) for r in cursor.fetchall()]

        # Recommendations
        recommendations = get_user_recommendations(user_id=user_id, limit=50)

        return {
            "plans": plans,
            "attempts": attempts,
            "recommendations": recommendations,
        }
    finally:
        conn.close()
