import pytest
from unittest.mock import patch
from database import init_db, get_or_create_user, save_study_plan, get_plan_topics, save_quiz_attempt
from recommendation_engine import generate_adaptive_guidance, get_topic_analytics
from utils.helpers import get_performance_tier

@pytest.fixture
def rec_db(tmp_path):
    db_file = str(tmp_path / "test_rec.db")
    init_db(db_file)
    return db_file

def test_low_quiz_score_recommendation(rec_db):
    """
    Scenario 8: Low quiz score recommendation (<50%).
    Recommends revision, identifies weak concepts, and advises simpler breakdown.
    """
    tier = get_performance_tier(40.0)
    assert tier["tier"] == "LOW"
    assert "Revision" in tier["label"]

    with patch("recommendation_engine.save_recommendation") as mock_save:
        mock_save.return_value = 1
        guidance = generate_adaptive_guidance(
            user_id=1,
            topic_id=10,
            score_percentage=40.0,
            correct_answers=2,
            total_questions=5,
            topic_name="Python Loops",
            level="Beginner",
            incorrect_questions=[{"question_text": "While loops", "correct_answer": "Repeats"}],
            db_path=rec_db,
        )
        assert guidance["score_percentage"] == 40.0
        assert guidance["tier_info"]["tier"] == "LOW"
        assert guidance["recommendations"]["recommendation_type"] == "revision"
        assert "revise" in guidance["recommendations"]["detailed_advice"].lower()

def test_high_quiz_score_recommendation(rec_db):
    """
    Scenario 9: High quiz score recommendation (>=85%).
    Recommends progression and suggests a mini-project.
    """
    tier = get_performance_tier(90.0)
    assert tier["tier"] == "HIGH"
    assert "Progress" in tier["label"]

    with patch("recommendation_engine.save_recommendation") as mock_save:
        mock_save.return_value = 2
        guidance = generate_adaptive_guidance(
            user_id=1,
            topic_id=11,
            score_percentage=90.0,
            correct_answers=9,
            total_questions=10,
            topic_name="Python Functions",
            level="Intermediate",
            db_path=rec_db,
        )
        assert guidance["score_percentage"] == 90.0
        assert guidance["tier_info"]["tier"] == "HIGH"

        assert guidance["recommendations"]["recommendation_type"] == "progression"
        assert "mini_project_or_challenge" in guidance["recommendations"]

def test_topic_analytics_categorization(rec_db):
    """Verify weak and strong topic detection from actual quiz history."""
    user_id = get_or_create_user("AnalyticsStudent", rec_db)
    plan_dict = {
        "days": [
            {"day_number": 1, "topic_name": "Topic A - Hard", "objectives": [], "estimated_time_minutes": 30},
            {"day_number": 2, "topic_name": "Topic B - Easy", "objectives": [], "estimated_time_minutes": 30},
        ]
    }
    plan_id = save_study_plan(user_id, "Subject", "Goal", plan_dict, rec_db)
    topics = get_plan_topics(plan_id, rec_db)
    t1_id = topics[0]["id"]
    t2_id = topics[1]["id"]

    # Attempt on Topic A: 40% (Weak)
    save_quiz_attempt(user_id, t1_id, 5, 2, 40.0, [], rec_db)
    # Attempt on Topic B: 90% (Strong)
    save_quiz_attempt(user_id, t2_id, 5, 4, 90.0, [], rec_db)

    analytics = get_topic_analytics(user_id, db_path=rec_db)
    assert len(analytics["weak_topics"]) == 1
    assert analytics["weak_topics"][0]["topic_name"] == "Topic A - Hard"
    assert len(analytics["strong_topics"]) == 1
    assert analytics["strong_topics"][0]["topic_name"] == "Topic B - Easy"

