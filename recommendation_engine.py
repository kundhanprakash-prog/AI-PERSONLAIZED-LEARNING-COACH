import logging
from typing import Dict, Any, List, Optional
from database import (
    save_recommendation,
    get_user_recommendations,
    get_quiz_attempts_for_user,
    get_topic_by_id,
)
from ai_service import generate_learning_recommendations, evaluate_learning_performance
from utils.helpers import get_performance_tier

logger = logging.getLogger(__name__)

def generate_adaptive_guidance(
    user_id: int,
    topic_id: int,
    score_percentage: float,
    correct_answers: int,
    total_questions: int,
    topic_name: str,
    level: str = "Beginner",
    incorrect_questions: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate tailored adaptive learning recommendations from actual quiz performance,
    save the recommendation to SQLite, and return the combined analysis.
    """
    # 1. Fetch past attempts for this topic to track improvement
    try:
        past_attempts = get_quiz_attempts_for_user(user_id=user_id, topic_id=topic_id, db_path=db_path)
    except Exception:
        past_attempts = []
    attempt_count = len(past_attempts)

    # 2. Extract weak concepts from missed questions
    weak_concepts = []
    if incorrect_questions:
        for item in incorrect_questions:
            q_text = item.get("question_text", "")
            ans = item.get("correct_answer", "")
            weak_concepts.append(f"{q_text[:60]}... (Key: {ans})")

    # 3. AI Performance Evaluation
    evaluation = evaluate_learning_performance(
        score_percentage=score_percentage,
        correct_answers=correct_answers,
        total_questions=total_questions,
        topic_name=topic_name,
        incorrect_questions=incorrect_questions,
        history=past_attempts,
        api_key=api_key,
    )

    # 4. Adaptive Recommendations
    recommendations = generate_learning_recommendations(
        score_percentage=score_percentage,
        topic_name=topic_name,
        level=level,
        weak_concepts=weak_concepts,
        api_key=api_key,
    )

    # 5. Persist recommendation in SQLite
    rec_type = recommendations.get("recommendation_type", "practice")
    detailed_rec_text = (
        f"{recommendations.get('recommendation_headline', '')}: "
        f"{recommendations.get('detailed_advice', '')} | "
        f"Next: {recommendations.get('recommended_next_step', '')}"
    )

    try:
        save_recommendation(
            user_id=user_id,
            topic_id=topic_id,
            recommendation=detailed_rec_text,
            recommendation_type=rec_type,
            db_path=db_path,
        )
    except Exception as e:
        logger.warning(f"Could not persist recommendation: {e}")

    return {
        "user_id": user_id,
        "topic_id": topic_id,
        "topic_name": topic_name,
        "score_percentage": score_percentage,
        "tier_info": get_performance_tier(score_percentage),
        "attempt_count": attempt_count,
        "evaluation": evaluation,
        "recommendations": recommendations,
        "weak_concepts": weak_concepts,
    }

def get_topic_analytics(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Classify topics into Strong, Moderate, and Weak based on average quiz scores.
    Uses actual SQLite quiz attempt data.
    """
    attempts = get_quiz_attempts_for_user(user_id, db_path=db_path)

    if not attempts:
        return {
            "strong_topics": [],
            "moderate_topics": [],
            "weak_topics": [],
            "total_attempts": 0,
            "average_score": 0.0,
        }

    # Group scores by topic
    topic_scores: Dict[str, List[float]] = {}
    for att in attempts:
        name = att.get("topic_name", "Unknown Topic")
        score = att.get("score_percentage", 0.0)
        topic_scores.setdefault(name, []).append(score)

    strong_topics = []
    moderate_topics = []
    weak_topics = []

    for name, scores in topic_scores.items():
        avg = round(sum(scores) / len(scores), 1)
        item = {
            "topic_name": name,
            "average_score": avg,
            "attempts": len(scores),
            "latest_score": scores[0], # first is latest due to ORDER BY submitted_at DESC
        }
        if avg >= 85.0:
            strong_topics.append(item)
        elif avg >= 70.0:
            moderate_topics.append(item)
        else:
            weak_topics.append(item)

    # Sort topics
    strong_topics.sort(key=lambda x: x["average_score"], reverse=True)
    weak_topics.sort(key=lambda x: x["average_score"])

    all_scores = [att["score_percentage"] for att in attempts]
    avg_total = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    return {
        "strong_topics": strong_topics,
        "moderate_topics": moderate_topics,
        "weak_topics": weak_topics,
        "total_attempts": len(attempts),
        "average_score": avg_total,
    }
