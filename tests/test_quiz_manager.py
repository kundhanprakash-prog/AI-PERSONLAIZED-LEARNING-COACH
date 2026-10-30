import pytest
from unittest.mock import patch
from database import init_db, get_or_create_user, save_study_plan, get_plan_topics
from quiz_manager import fetch_topic_quiz, evaluate_and_record_quiz, get_topic_quiz_history
from utils.helpers import calculate_score

@pytest.fixture
def quiz_db(tmp_path):
    db_file = str(tmp_path / "test_quiz.db")
    init_db(db_file)
    return db_file

def test_quiz_generation():
    """Scenario 5: Quiz generation produces 5 MCQs."""
    success, questions, msg = fetch_topic_quiz("Python Loops", level="Beginner", count=5)
    assert success is True
    assert len(questions) == 5
    for q in questions:
        assert "question_text" in q
        assert len(q["options"]) == 4
        assert "correct_answer" in q

def test_python_quiz_scoring_independent_of_gemini(quiz_db):
    """
    Scenario 6 & 7: Python scoring works independently of Gemini.
    Correct scoring and incorrect scoring are calculated mathematically.
    """
    user_id = get_or_create_user("StudentQuiz", quiz_db)
    plan_dict = {"days": [{"day_number": 1, "topic_name": "Loops", "objectives": [], "estimated_time_minutes": 30}]}
    plan_id = save_study_plan(user_id, "Python", "Goal", plan_dict, quiz_db)
    topics = get_plan_topics(plan_id, quiz_db)
    topic_id = topics[0]["id"]

    mock_questions = [
        {
            "question_text": "What does a while loop do?",
            "options": ["Repeats while condition is True", "Runs only once", "Never runs", "Halts CPU"],
            "correct_answer": "Repeats while condition is True",
            "explanation": "While loops execute their block as long as the test expression evaluates to True.",
        },
        {
            "question_text": "Which statement exits a loop prematurely?",
            "options": ["break", "continue", "pass", "return"],
            "correct_answer": "break",
            "explanation": "break terminates the nearest enclosing loop.",
        },
        {
            "question_text": "Which statement skips the current iteration?",
            "options": ["continue", "break", "pass", "stop"],
            "correct_answer": "continue",
            "explanation": "continue rejects remaining statements in the current iteration and moves to next.",
        },
        {
            "question_text": "What does range(3) produce?",
            "options": ["0, 1, 2", "1, 2, 3", "0, 1, 2, 3", "1, 2"],
            "correct_answer": "0, 1, 2",
            "explanation": "range(n) starts from 0 up to n-1.",
        },
        {
            "question_text": "Can a for loop have an else block in Python?",
            "options": ["Yes, executed if loop completes without break", "No, else is only for if", "Only in Python 2", "Causes SyntaxError"],
            "correct_answer": "Yes, executed if loop completes without break",
            "explanation": "Python for-else runs else when the loop completes naturally.",
        },
    ]

    # Perfect Score (5/5 = 100%)
    with patch("quiz_manager.save_quiz_attempt") as mock_save:
        mock_save.return_value = 1
        perfect_answers = {
            0: "Repeats while condition is True",
            1: "break",
            2: "continue",
            3: "0, 1, 2",
            4: "Yes, executed if loop completes without break",
        }
        res_perfect = evaluate_and_record_quiz(user_id, topic_id, mock_questions, perfect_answers)
        assert res_perfect["correct_answers"] == 5
        assert res_perfect["score_percentage"] == 100.0
        assert res_perfect["performance_tier"]["tier"] == "HIGH"

    # 4 out of 5 (80%)
    with patch("quiz_manager.save_quiz_attempt") as mock_save:
        mock_save.return_value = 2
        four_answers = {
            0: "Repeats while condition is True",
            1: "break",
            2: "continue",
            3: "0, 1, 2",
            4: "Wrong answer",
        }
        res_four = evaluate_and_record_quiz(user_id, topic_id, mock_questions, four_answers)
        assert res_four["correct_answers"] == 4
        assert res_four["incorrect_answers"] == 1
        assert res_four["score_percentage"] == 80.0
        assert res_four["performance_tier"]["tier"] == "GOOD"

    # Low Score (1 out of 5 = 20%)
    with patch("quiz_manager.save_quiz_attempt") as mock_save:
        mock_save.return_value = 3
        low_answers = {
            0: "Repeats while condition is True",
            1: "wrong",
            2: "wrong",
            3: "wrong",
            4: "wrong",
        }
        res_low = evaluate_and_record_quiz(user_id, topic_id, mock_questions, low_answers)
        assert res_low["correct_answers"] == 1
        assert res_low["incorrect_answers"] == 4
        assert res_low["score_percentage"] == 20.0
        assert res_low["performance_tier"]["tier"] == "LOW"

def test_repeated_quiz_attempts(quiz_db):
    """Scenario 11: Repeated quiz attempts recorded and tracked independently."""
    user_id = get_or_create_user("RepeatStudent", quiz_db)
    plan_dict = {"days": [{"day_number": 1, "topic_name": "Recursion", "objectives": [], "estimated_time_minutes": 30}]}
    plan_id = save_study_plan(user_id, "DSA", "Goal", plan_dict, quiz_db)
    topics = get_plan_topics(plan_id, quiz_db)
    topic_id = topics[0]["id"]

    mock_q = [{
        "question_text": "Base case purpose?",
        "options": ["Stop recursion", "Loop infinitely", "Crash program", "No purpose"],
        "correct_answer": "Stop recursion",
        "explanation": "Base case halts recursion.",
    }]

    # Attempt 1: Failed
    res1 = evaluate_and_record_quiz(user_id, topic_id, mock_q, {0: "Crash program"}, db_path=quiz_db)
    assert res1["score_percentage"] == 0.0

    # Attempt 2: Passed
    res2 = evaluate_and_record_quiz(user_id, topic_id, mock_q, {0: "Stop recursion"}, db_path=quiz_db)
    assert res2["score_percentage"] == 100.0

    history = get_topic_quiz_history(user_id, topic_id, db_path=quiz_db)
    assert len(history) == 2
    # Most recent first
    assert history[0]["score_percentage"] == 100.0
    assert history[1]["score_percentage"] == 0.0

