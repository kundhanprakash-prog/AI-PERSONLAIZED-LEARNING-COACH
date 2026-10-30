import pytest
from validators import (
    validate_learner_profile,
    validate_study_plan_structure,
    validate_quiz_structure,
)

def test_missing_subject_or_goal():
    """Scenario 1: Missing subject or goal should fail validation."""
    # Empty subject
    valid, msg = validate_learner_profile("Alice", "", "Learn Python", "Beginner", 7, 45)
    assert not valid
    assert "Subject is required" in msg

    # Empty goal
    valid, msg = validate_learner_profile("Alice", "Python", "", "Beginner", 7, 45)
    assert not valid
    assert "Learning goal is required" in msg

    # Too short goal
    valid, msg = validate_learner_profile("Alice", "Python", "abc", "Beginner", 7, 45)
    assert not valid
    assert "at least 5 characters" in msg

def test_valid_student_setup():
    """Scenario 2: Valid student setup passes validation."""
    valid, msg = validate_learner_profile(
        name="John Doe",
        subject="Data Science",
        learning_goal="Master Pandas and Machine Learning algorithms",
        current_level="Intermediate",
        target_duration=14,
        daily_study_time=60,
    )
    assert valid
    assert msg == ""

def test_invalid_user_inputs():
    """Scenario 13: Invalid user inputs (duration, study time, level)."""
    # Empty name
    valid, msg = validate_learner_profile("", "Python", "Learn Basics", "Beginner", 7, 45)
    assert not valid

    # Invalid level
    valid, msg = validate_learner_profile("Bob", "Python", "Learn Basics", "Expert", 7, 45)
    assert not valid
    assert "Current level must be one of" in msg

    # Invalid duration (zero or negative)
    valid, msg = validate_learner_profile("Bob", "Python", "Learn Basics", "Beginner", 0, 45)
    assert not valid
    assert "Target duration must be between 1 and 90 days" in msg

    # Invalid duration (non-numeric)
    valid, msg = validate_learner_profile("Bob", "Python", "Learn Basics", "Beginner", "abc", 45)
    assert not valid
    assert "valid positive integer" in msg

    # Study time too low (<15 mins)
    valid, msg = validate_learner_profile("Bob", "Python", "Learn Basics", "Beginner", 7, 5)
    assert not valid
    assert "Daily study time must be between" in msg

def test_validate_study_plan_structure():
    """Valid and invalid study plan structure."""
    # Valid
    valid_plan = {
        "days": [
            {
                "day_number": 1,
                "topic_name": "Variables",
                "objectives": ["Obj 1"],
                "estimated_time_minutes": 30,
            }
        ]
    }
    assert validate_study_plan_structure(valid_plan)[0] is True

    # Missing days
    assert validate_study_plan_structure({})[0] is False
    assert validate_study_plan_structure({"days": []})[0] is False

    # Missing topic_name
    invalid_plan = {"days": [{"day_number": 1, "objectives": []}]}
    assert validate_study_plan_structure(invalid_plan)[0] is False

def test_validate_quiz_structure():
    """Valid and invalid quiz structure."""
    valid_quiz = [
        {
            "question_text": "What is Python?",
            "options": ["A programming language", "A snake only", "A text editor", "An OS"],
            "correct_answer": "A programming language",
            "explanation": "Python is a high-level interpreted programming language.",
            "difficulty": "Easy",
            "related_topic": "Intro",
        }
    ]
    assert validate_quiz_structure(valid_quiz)[0] is True

    # Less than 4 options
    invalid_quiz = [
        {
            "question_text": "What is Python?",
            "options": ["Option 1", "Option 2"],
            "correct_answer": "Option 1",
        }
    ]
    assert validate_quiz_structure(invalid_quiz)[0] is False
