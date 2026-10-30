import logging
from typing import Dict, Any, List, Optional, Tuple
from database import (
    save_quiz_attempt,
    get_quiz_attempts_for_user,
    get_attempt_responses,
    get_topic_by_id,
)
from ai_service import generate_quiz
from utils.helpers import calculate_score, get_performance_tier
from validators import validate_quiz_structure

logger = logging.getLogger(__name__)

def fetch_topic_quiz(
    topic_name: str,
    level: str = "Beginner",
    count: int = 5,
    subject: str = "",
    api_key: Optional[str] = None,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Generate and validate 5 MCQs for a selected study topic using Gemini.
    """
    try:
        questions = generate_quiz(
            topic_name=topic_name,
            level=level,
            count=count,
            subject=subject,
            api_key=api_key,
        )
        is_valid, err_msg = validate_quiz_structure(questions)
        if not is_valid:
            logger.warning(f"Quiz validation warning: {err_msg}")
        return True, questions, "Quiz questions successfully generated."
    except Exception as e:
        logger.error(f"Failed to generate quiz for topic '{topic_name}': {e}")
        return False, [], f"Error generating quiz: {str(e)}"

def evaluate_and_record_quiz(
    user_id: int,
    topic_id: int,
    questions: List[Dict[str, Any]],
    user_answers: Dict[int, str],
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Score the quiz strictly using Python logic, comparing user selection with the answer key.
    Persist attempt and individual question responses into SQLite.
    Returns complete evaluation summary.
    """
    total_questions = len(questions)
    correct_count = 0
    detailed_responses = []

    for idx, q in enumerate(questions):
        selected = str(user_answers.get(idx, "")).strip()
        correct_raw = str(q.get("correct_answer", "")).strip()
        explanation = q.get("explanation", "")
        options = q.get("options", [])

        # Match check
        is_correct = False
        # Direct verbatim match
        if selected and selected.lower() == correct_raw.lower():
            is_correct = True
        # Handle 'A', 'B', 'C', 'D' mapping if correct_raw is letter
        elif correct_raw.upper() in ["A", "B", "C", "D"]:
            letter_idx = ord(correct_raw.upper()) - ord("A")
            if 0 <= letter_idx < len(options):
                if selected.lower() == str(options[letter_idx]).strip().lower():
                    is_correct = True
        # Handle option prefixed with letter (e.g. "A) Python")
        elif selected:
            for opt in options:
                opt_str = str(opt).strip()
                if opt_str.startswith(correct_raw) and selected.lower() == opt_str.lower():
                    is_correct = True
                    break

        if is_correct:
            correct_count += 1

        detailed_responses.append({
            "question_index": idx + 1,
            "question_text": q.get("question_text", ""),
            "selected_answer": selected or "No answer provided",
            "correct_answer": correct_raw,
            "is_correct": is_correct,
            "explanation": explanation,
            "difficulty": q.get("difficulty", "Medium"),
            "related_topic": q.get("related_topic", ""),
        })

    # Python calculates the exact score
    _, _, score_pct = calculate_score(correct_count, total_questions)
    tier_info = get_performance_tier(score_pct)

    # Save to SQLite
    attempt_id = save_quiz_attempt(
        user_id=user_id,
        topic_id=topic_id,
        total_questions=total_questions,
        correct_answers=correct_count,
        score_percentage=score_pct,
        responses=detailed_responses,
        db_path=db_path,
    )

    return {
        "attempt_id": attempt_id,
        "user_id": user_id,
        "topic_id": topic_id,
        "total_questions": total_questions,
        "correct_answers": correct_count,
        "incorrect_answers": total_questions - correct_count,
        "score_percentage": score_pct,
        "performance_tier": tier_info,
        "responses": detailed_responses,
        "incorrect_questions": [r for r in detailed_responses if not r["is_correct"]],
    }

def get_topic_quiz_history(user_id: int, topic_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all past quiz attempts for a user on a specific topic."""
    return get_quiz_attempts_for_user(user_id=user_id, topic_id=topic_id, db_path=db_path)

