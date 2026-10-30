import logging
from typing import Dict, Any, List, Optional, Tuple
from database import (
    save_study_plan,
    get_study_plan,
    get_user_study_plans,
    get_plan_topics,
    update_topic_status,
    get_topic_by_id,
)
from ai_service import generate_study_plan
from validators import validate_learner_profile, validate_study_plan_structure

logger = logging.getLogger(__name__)

def create_and_save_study_plan(
    user_id: int,
    subject: str,
    learning_goal: str,
    current_level: str,
    target_duration: int,
    daily_study_time: int,
    approach: str = "",
    user_name: str = "Learner",
    api_key: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Tuple[bool, Optional[int], Dict[str, Any], str]:
    """
    Validate inputs, request AI study plan generation, and save into database.
    Returns (success, plan_id, plan_dict, message)
    """
    # 1. Validate inputs
    is_valid, err_msg = validate_learner_profile(
        name=user_name,
        subject=subject,
        learning_goal=learning_goal,
        current_level=current_level,
        target_duration=target_duration,
        daily_study_time=daily_study_time,
    )
    if not is_valid:
        return False, None, {}, err_msg

    try:
        # 2. Call AI Service
        plan_dict = generate_study_plan(
            subject=subject,
            learning_goal=learning_goal,
            current_level=current_level,
            target_duration=int(target_duration),
            daily_study_time=int(daily_study_time),
            approach=approach,
            api_key=api_key,
        )

        # 3. Validate Plan Structure
        valid_struct, struct_err = validate_study_plan_structure(plan_dict)
        if not valid_struct:
            return False, None, {}, f"Generated plan structure was invalid: {struct_err}"

        # 4. Save into SQLite
        plan_id = save_study_plan(
            user_id=user_id,
            subject=subject,
            learning_goal=learning_goal,
            plan_dict=plan_dict,
            db_path=db_path,
        )

        return True, plan_id, plan_dict, "Study plan successfully created and saved!"

    except Exception as e:
        logger.error(f"Error creating study plan: {e}")
        return False, None, {}, f"Failed to generate study plan: {str(e)}"

def get_plan_summary(plan_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive statistics for a study plan:
    Total topics, completed topics, pending topics, percentage, etc.
    """
    plan = get_study_plan(plan_id, db_path=db_path)
    if not plan:
        return None

    topics = get_plan_topics(plan_id, db_path=db_path)
    total_topics = len(topics)
    completed_topics = sum(1 for t in topics if t.get("status") == "completed")
    pending_topics = total_topics - completed_topics
    pct = round((completed_topics / total_topics * 100.0), 1) if total_topics > 0 else 0.0

    total_est_minutes = sum(t.get("estimated_time", 0) for t in topics)
    remaining_minutes = sum(
        t.get("estimated_time", 0) for t in topics if t.get("status") != "completed"
    )

    return {
        "plan_id": plan_id,
        "subject": plan.get("subject"),
        "learning_goal": plan.get("learning_goal"),
        "created_at": plan.get("created_at"),
        "status": plan.get("status"),
        "total_days": len(set(t.get("day_number", 1) for t in topics)),
        "total_topics": total_topics,
        "completed_topics": completed_topics,
        "pending_topics": pending_topics,
        "completion_percentage": pct,
        "total_est_minutes": total_est_minutes,
        "remaining_minutes": remaining_minutes,
        "topics": topics,
        "plan_data": plan.get("plan_data", {}),
    }

def mark_topic_completed(topic_id: int, db_path: Optional[str] = None) -> bool:
    """Mark a study topic as completed."""
    return update_topic_status(topic_id, "completed", db_path=db_path)

def mark_topic_pending(topic_id: int, db_path: Optional[str] = None) -> bool:
    """Mark a study topic as pending."""
    return update_topic_status(topic_id, "pending", db_path=db_path)

