import os
import sqlite3
import pytest
from database import (
    init_db,
    get_connection,
    get_or_create_user,
    save_learner_profile,
    get_latest_profile,
    save_study_plan,
    get_study_plan,
    get_plan_topics,
    update_topic_status,
    save_quiz_attempt,
    get_quiz_attempts_for_user,
    get_attempt_responses,
    save_recommendation,
    get_user_recommendations,
)

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database file."""
    db_file = str(tmp_path / "test_learning_coach.db")
    init_db(db_file)
    return db_file

def test_database_initialization(test_db):
    """Verify tables exist and foreign keys are enabled."""
    conn = get_connection(test_db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()

    expected_tables = [
        "users",
        "learner_profiles",
        "study_plans",
        "study_topics",
        "quiz_attempts",
        "quiz_responses",
        "learning_recommendations",
    ]
    for table in expected_tables:
        assert table in tables

def test_user_and_profile_crud(test_db):
    """Test user creation and profile storage."""
    user_id = get_or_create_user("Jane Doe", test_db)
    assert user_id > 0

    # Idempotent user get
    user_id_2 = get_or_create_user("Jane Doe", test_db)
    assert user_id == user_id_2

    profile_id = save_learner_profile(
        user_id=user_id,
        subject="Python",
        learning_goal="Backend Development",
        current_level="Beginner",
        target_duration=7,
        daily_study_time=45,
        db_path=test_db,
    )
    assert profile_id > 0

    profile = get_latest_profile(user_id, test_db)
    assert profile is not None
    assert profile["subject"] == "Python"
    assert profile["target_duration"] == 7

def test_study_plan_and_topic_persistence(test_db):
    """Scenario 10: SQLite persistence after application restart/reconnection."""
    user_id = get_or_create_user("Bob", test_db)
    plan_dict = {
        "days": [
            {
                "day_number": 1,
                "topic_name": "Variables & Types",
                "objectives": ["Understand int, str"],
                "estimated_time_minutes": 45,
            },
            {
                "day_number": 2,
                "topic_name": "Loops",
                "objectives": ["Master for loops"],
                "estimated_time_minutes": 45,
            },
        ]
    }
    plan_id = save_study_plan(user_id, "Python", "Learn Basics", plan_dict, test_db)
    assert plan_id > 0

    # Simulate fresh connection
    topics = get_plan_topics(plan_id, test_db)
    assert len(topics) == 2
    assert topics[0]["topic_name"] == "Variables & Types"
    assert topics[0]["status"] == "pending"

    # Mark completed
    t1_id = topics[0]["id"]
    success = update_topic_status(t1_id, "completed", test_db)
    assert success is True

    # Reconnect and verify completion persists
    updated_topics = get_plan_topics(plan_id, test_db)
    assert updated_topics[0]["status"] == "completed"
    assert updated_topics[0]["completed_at"] is not None

def test_foreign_key_constraints(test_db):
    """Scenario 14: Database errors on foreign key constraint violation."""
    conn = get_connection(test_db)
    with pytest.raises(sqlite3.IntegrityError):
        # Attempting to insert a profile for a non-existent user_id 9999
        conn.execute(
            """
            INSERT INTO learner_profiles (
                user_id, subject, learning_goal, current_level, target_duration, daily_study_time
            ) VALUES (9999, 'Test', 'Goal', 'Beginner', 7, 30)
            """
        )
    conn.close()

def test_quiz_attempt_and_responses_persistence(test_db):
    """Test saving quiz attempt and detailed question responses."""
    user_id = get_or_create_user("Charlie", test_db)
    plan_dict = {"days": [{"day_number": 1, "topic_name": "Conditionals", "objectives": [], "estimated_time_minutes": 30}]}
    plan_id = save_study_plan(user_id, "Logic", "Goal", plan_dict, test_db)
    topics = get_plan_topics(plan_id, test_db)
    topic_id = topics[0]["id"]

    responses = [
        {
            "question_text": "Is 5 > 3?",
            "selected_answer": "Yes",
            "correct_answer": "Yes",
            "is_correct": True,
            "explanation": "5 is indeed greater than 3.",
        },
        {
            "question_text": "Is 2 > 10?",
            "selected_answer": "Yes",
            "correct_answer": "No",
            "is_correct": False,
            "explanation": "2 is less than 10.",
        },
    ]

    attempt_id = save_quiz_attempt(
        user_id=user_id,
        topic_id=topic_id,
        total_questions=2,
        correct_answers=1,
        score_percentage=50.0,
        responses=responses,
        db_path=test_db,
    )
    assert attempt_id > 0

    attempts = get_quiz_attempts_for_user(user_id=user_id, db_path=test_db)
    assert len(attempts) == 1
    assert attempts[0]["score_percentage"] == 50.0

    stored_responses = get_attempt_responses(attempt_id, test_db)
    assert len(stored_responses) == 2
    assert stored_responses[0]["is_correct"] == 1
    assert stored_responses[1]["is_correct"] == 0

def test_learning_recommendation_crud(test_db):
    """Test saving and retrieving learning recommendations."""
    user_id = get_or_create_user("David", test_db)
    rec_id = save_recommendation(
        user_id=user_id,
        topic_id=None,
        recommendation="Revise control flow loops",
        recommendation_type="revision",
        db_path=test_db,
    )
    assert rec_id > 0
    recs = get_user_recommendations(user_id, db_path=test_db)
    assert len(recs) == 1
    assert recs[0]["recommendation_type"] == "revision"
