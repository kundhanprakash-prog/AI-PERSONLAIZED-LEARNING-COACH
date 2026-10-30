import pytest
from unittest.mock import patch
from database import init_db, get_or_create_user
from learning_plan import create_and_save_study_plan, get_plan_summary, mark_topic_completed
from ai_service import generate_study_plan

@pytest.fixture
def plan_db(tmp_path):
    db_file = str(tmp_path / "test_plan.db")
    init_db(db_file)
    return db_file

def test_study_plan_generation_dynamic(plan_db):
    """Scenario 3: Study plan generation for a target duration and daily time."""
    user_id = get_or_create_user("TestStudent", plan_db)

    success, plan_id, plan_dict, msg = create_and_save_study_plan(
        user_id=user_id,
        subject="Python",
        learning_goal="Build REST APIs with FastAPI",
        current_level="Intermediate",
        target_duration=5,
        daily_study_time=45,
        user_name="TestStudent",
        db_path=plan_db,
    )
    assert success is True
    assert plan_id is not None
    assert "days" in plan_dict
    assert len(plan_dict["days"]) == 5

    # Check summary calculation
    summary = get_plan_summary(plan_id, db_path=plan_db)
    assert summary is not None
    assert summary["total_topics"] == 5
    assert summary["completed_topics"] == 0
    assert summary["pending_topics"] == 5
    assert summary["completion_percentage"] == 0.0

    # Mark first topic completed
    first_topic_id = summary["topics"][0]["id"]
    mark_topic_completed(first_topic_id, db_path=plan_db)

    updated_summary = get_plan_summary(plan_id, db_path=plan_db)
    assert updated_summary["completed_topics"] == 1
    assert updated_summary["completion_percentage"] == 20.0


def test_invalid_gemini_response_handling():
    """Scenario 4 & Scenario 12: Invalid Gemini response / API failure handled gracefully."""
    # When Gemini API fails or returns invalid JSON, fallback generator provides a structured plan
    with patch("ai_service._call_gemini_with_fallback", side_effect=Exception("API Connection Refused")):
        plan = generate_study_plan(
            subject="JavaScript",
            learning_goal="Learn modern ES6+ concepts",
            current_level="Beginner",
            target_duration=3,
            daily_study_time=30,
        )
        assert plan is not None
        assert "days" in plan
        assert len(plan["days"]) == 3
        assert plan.get("is_fallback") is True
