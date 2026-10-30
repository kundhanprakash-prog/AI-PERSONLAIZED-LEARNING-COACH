import os
import pytest
from database import (
    init_db,
    get_or_create_user,
    save_learner_profile,
    get_latest_profile,
    get_plan_topics,
    get_study_plan,
    get_quiz_attempts_for_user,
    update_topic_status,
)
from learning_plan import create_and_save_study_plan, get_plan_summary, mark_topic_completed
from quiz_manager import fetch_topic_quiz, evaluate_and_record_quiz
from recommendation_engine import generate_adaptive_guidance, get_topic_analytics
from analytics import get_dashboard_metrics, get_full_learning_history

@pytest.fixture
def e2e_db(tmp_path):
    db_file = str(tmp_path / "e2e_learning_coach.db")
    init_db(db_file)
    return db_file

def test_full_student_journey(e2e_db):
    """
    Test the complete 15-step end-to-end workflow:
    1. Student onboarding & profile saving
    2. Dynamic study plan generation
    3. Topic listing & verification
    4. 5-question MCQ assessment generation
    5. Python-based deterministic scoring
    6. Identification of weak/strong concepts
    7. Adaptive recommendation generation & SQLite storage
    8. Dashboard telemetry retrieval
    9. Verification that all historical data survives simulated app restarts
    """
    # Step 1: Student Setup
    student_name = "Elena Rostova"
    user_id = get_or_create_user(student_name, db_path=e2e_db)
    assert user_id > 0

    profile_id = save_learner_profile(
        user_id=user_id,
        subject="Python Programming",
        learning_goal="Master backend APIs with FastAPI and databases",
        current_level="Beginner",
        target_duration=7,
        daily_study_time=45,
        db_path=e2e_db,
    )
    assert profile_id > 0

    latest_profile = get_latest_profile(user_id, db_path=e2e_db)
    assert latest_profile["subject"] == "Python Programming"

    # Step 2: Study Plan Generation
    success, plan_id, plan_dict, msg = create_and_save_study_plan(
        user_id=user_id,
        subject=latest_profile["subject"],
        learning_goal=latest_profile["learning_goal"],
        current_level=latest_profile["current_level"],
        target_duration=latest_profile["target_duration"],
        daily_study_time=latest_profile["daily_study_time"],
        user_name=student_name,
        db_path=e2e_db,
    )
    assert success is True
    assert plan_id is not None
    assert len(plan_dict["days"]) == 7

    # Step 3: Check Topics
    topics = get_plan_topics(plan_id, db_path=e2e_db)
    assert len(topics) == 7
    topic_1 = topics[0]
    topic_1_id = topic_1["id"]
    topic_1_name = topic_1["topic_name"]

    # Step 4: Quiz Generation (5 MCQs)
    quiz_ok, questions, quiz_msg = fetch_topic_quiz(topic_1_name, level="Beginner", count=5)
    assert quiz_ok is True
    assert len(questions) == 5

    # Step 5 & 6: Student Submits Answers -> Python scores without Gemini
    user_answers = {
        0: questions[0]["correct_answer"],
        1: questions[1]["correct_answer"],
        2: questions[2]["correct_answer"],
        3: questions[3]["correct_answer"],
        4: "Incorrect intentional choice",
    }
    eval_result = evaluate_and_record_quiz(
        user_id=user_id,
        topic_id=topic_1_id,
        questions=questions,
        user_answers=user_answers,
        db_path=e2e_db,
    )

    # 4 out of 5 correct = 80.0%
    assert eval_result["total_questions"] == 5
    assert eval_result["correct_answers"] == 4
    assert eval_result["incorrect_answers"] == 1
    assert eval_result["score_percentage"] == 80.0
    assert eval_result["performance_tier"]["tier"] == "GOOD"

    # Step 7: Adaptive Guidance & Weak Topic Identification
    guidance = generate_adaptive_guidance(
        user_id=user_id,
        topic_id=topic_1_id,
        score_percentage=eval_result["score_percentage"],
        correct_answers=eval_result["correct_answers"],
        total_questions=eval_result["total_questions"],
        topic_name=topic_1_name,
        level="Beginner",
        incorrect_questions=eval_result["incorrect_questions"],
        db_path=e2e_db,
    )
    assert guidance["score_percentage"] == 80.0
    assert "recommendations" in guidance

    # Mark topic completed
    mark_topic_completed(topic_1_id, db_path=e2e_db)

    # Step 8: Dashboard Metrics
    analytics = get_topic_analytics(user_id, db_path=e2e_db)
    assert analytics["total_attempts"] == 1
    assert analytics["average_score"] == 80.0
    assert len(analytics["moderate_topics"]) == 1

    # Step 9: Verify Persistence across fresh connections (simulated app restart)
    reloaded_plans = get_full_learning_history(user_id)
    # The history function uses default DATABASE_PATH, let's verify via get_quiz_attempts_for_user on e2e_db
    persisted_attempts = get_quiz_attempts_for_user(user_id=user_id, db_path=e2e_db)
    assert len(persisted_attempts) == 1
    assert persisted_attempts[0]["score_percentage"] == 80.0
    assert persisted_attempts[0]["topic_name"] == topic_1_name

    reloaded_topics = get_plan_topics(plan_id, db_path=e2e_db)
    assert reloaded_topics[0]["status"] == "completed"
    assert reloaded_topics[1]["status"] == "pending"
