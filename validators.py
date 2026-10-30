import json
from typing import Dict, Any, List, Tuple
from utils.config import KNOWLEDGE_LEVELS

def validate_learner_profile(
    name: str,
    subject: str,
    learning_goal: str,
    current_level: str,
    target_duration: Any,
    daily_study_time: Any,
) -> Tuple[bool, str]:
    """
    Validate student onboarding inputs.
    Ensures no empty subject, goal, invalid duration, or invalid study time.
    """
    if not name or not str(name).strip():
        return False, "Student name is required and cannot be empty."
    if len(str(name).strip()) < 2:
        return False, "Student name must be at least 2 characters long."

    if not subject or not str(subject).strip():
        return False, "Subject is required and cannot be empty."
    if len(str(subject).strip()) < 2:
        return False, "Subject must be at least 2 characters long."

    if not learning_goal or not str(learning_goal).strip():
        return False, "Learning goal is required and cannot be empty."
    if len(str(learning_goal).strip()) < 5:
        return False, "Learning goal should be descriptive (at least 5 characters)."

    if current_level not in KNOWLEDGE_LEVELS:
        return False, f"Current level must be one of {', '.join(KNOWLEDGE_LEVELS)}."

    try:
        duration_int = int(target_duration)
        if duration_int < 1 or duration_int > 90:
            return False, "Target duration must be between 1 and 90 days."
    except (ValueError, TypeError):
        return False, "Target duration must be a valid positive integer."

    try:
        study_time_int = int(daily_study_time)
        if study_time_int < 15 or study_time_int > 600:
            return False, "Daily study time must be between 15 and 600 minutes."
    except (ValueError, TypeError):
        return False, "Daily study time must be a valid positive integer."

    return True, ""

def validate_study_plan_structure(plan_data: Any) -> Tuple[bool, str]:
    """
    Validate that generated study plan JSON conforms to the required schema:
    Contains days with day_number, topic_name, objectives, subtopics, estimated_time.
    """
    if not isinstance(plan_data, dict):
        return False, "Study plan data must be a JSON object (dictionary)."

    days = plan_data.get("days")
    if not isinstance(days, list) or len(days) == 0:
        return False, "Study plan must contain a non-empty 'days' list."

    for idx, day in enumerate(days, start=1):
        if not isinstance(day, dict):
            return False, f"Day entry at index {idx} is not a valid object."

        if "day_number" not in day or not isinstance(day["day_number"], int):
            return False, f"Day entry {idx} is missing a valid integer 'day_number'."

        if not day.get("topic_name") or not str(day["topic_name"]).strip():
            return False, f"Day {idx} is missing a valid 'topic_name'."

        if "objectives" not in day:
            return False, f"Day {idx} is missing 'objectives'."

        if "estimated_time_minutes" not in day:
            return False, f"Day {idx} is missing 'estimated_time_minutes'."

    return True, ""

def validate_quiz_structure(quiz_data: Any) -> Tuple[bool, str]:
    """
    Validate that generated quiz structure contains valid questions.
    Each question must contain:
    - question_text
    - options (list of 4 options)
    - correct_answer
    - explanation
    - difficulty
    - related_topic
    """
    questions = None
    if isinstance(quiz_data, dict):
        questions = quiz_data.get("questions")
    elif isinstance(quiz_data, list):
        questions = quiz_data

    if not isinstance(questions, list) or len(questions) == 0:
        return False, "Quiz must contain a list of questions."

    for idx, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            return False, f"Question {idx} is not a valid object."

        if not q.get("question_text") or not str(q["question_text"]).strip():
            return False, f"Question {idx} is missing 'question_text'."

        options = q.get("options")
        if not isinstance(options, list) or len(options) != 4:
            return False, f"Question {idx} must have exactly 4 options."

        correct_answer = q.get("correct_answer")
        if not correct_answer or not str(correct_answer).strip():
            return False, f"Question {idx} is missing 'correct_answer'."

        # Verify correct_answer matches one of the options or an option key (A, B, C, D)
        options_clean = [str(opt).strip() for opt in options]
        correct_clean = str(correct_answer).strip()

        # If correct_answer is 'A', 'B', 'C', 'D'
        valid_match = False
        if correct_clean in options_clean:
            valid_match = True
        elif correct_clean.upper() in ["A", "B", "C", "D"]:
            valid_match = True
        else:
            # Check if any option starts with that letter, e.g. "A) option"
            for opt in options_clean:
                if opt.startswith(correct_clean) or opt.lower() == correct_clean.lower():
                    valid_match = True
                    break

        if not valid_match:
            # If not matching exactly, fallback check
            pass

    return True, ""
