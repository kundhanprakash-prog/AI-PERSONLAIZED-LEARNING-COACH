import json
from pathlib import Path
from database import (
    init_db,
    get_or_create_user,
    save_learner_profile,
    save_study_plan,
    update_topic_status,
    get_plan_topics,
    save_quiz_attempt,
    save_recommendation,
)

def seed_demo_data():
    """Seed initial student, study plan, and assessment history for demonstration."""
    init_db()
    
    # 1. Student User
    user_id = get_or_create_user("Alex Johnson")
    
    # 2. Learner Profile
    save_learner_profile(
        user_id=user_id,
        subject="Python Programming",
        learning_goal="Master backend engineering, data manipulation, and software design",
        current_level="Beginner",
        target_duration=7,
        daily_study_time=45,
    )
    
    # 3. Study Plan from sample_data
    sample_file = Path(__file__).resolve().parent / "sample_data" / "example_learning_plan.json"
    if sample_file.exists():
        with open(sample_file, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
    else:
        plan_data = {
            "subject": "Python Programming",
            "learning_goal": "Master Python fundamentals",
            "level": "Beginner",
            "target_duration_days": 7,
            "daily_study_time_minutes": 45,
            "days": [
                {
                    "day_number": 1,
                    "topic_name": "Python Variables and Data Types",
                    "objectives": ["Master integers, strings, booleans"],
                    "subtopics": ["Variables", "Type Casting"],
                    "estimated_time_minutes": 45,
                    "practice_activities": ["Write basic calculator"],
                    "resources": ["Official Python Tutorial"],
                },
                {
                    "day_number": 2,
                    "topic_name": "Operators and Conditional Statements",
                    "objectives": ["Use arithmetic and logical operators"],
                    "subtopics": ["If-Else branching"],
                    "estimated_time_minutes": 45,
                    "practice_activities": ["Build grade calculator"],
                    "resources": ["W3Schools Python Conditions"],
                },
            ]
        }
    
    plan_id = save_study_plan(
        user_id=user_id,
        subject="Python Programming",
        learning_goal="Master backend engineering, data manipulation, and software design",
        plan_dict=plan_data,
    )
    
    topics = get_plan_topics(plan_id)
    if topics:
        # Mark Day 1 as completed
        t1 = topics[0]
        update_topic_status(t1["id"], "completed")
        
        # Save a sample quiz attempt on Day 1
        responses = [
            {
                "question_text": "Which data type is used to represent decimal numbers in Python?",
                "selected_answer": "float",
                "correct_answer": "float",
                "is_correct": True,
                "explanation": "float represents double-precision floating-point numbers.",
            },
            {
                "question_text": "What is the output of type(10)?",
                "selected_answer": "<class 'int'>",
                "correct_answer": "<class 'int'>",
                "is_correct": True,
                "explanation": "10 is an integer literal.",
            },
            {
                "question_text": "Are Python variable names case-sensitive?",
                "selected_answer": "Yes",
                "correct_answer": "Yes",
                "is_correct": True,
                "explanation": "Variable and variable are treated as distinct identifiers.",
            },
            {
                "question_text": "Which function converts a numeric string '42' to an integer?",
                "selected_answer": "int('42')",
                "correct_answer": "int('42')",
                "is_correct": True,
                "explanation": "int() parses string literals to integers.",
            },
            {
                "question_text": "Which of the following is an invalid variable name in Python?",
                "selected_answer": "2nd_variable",
                "correct_answer": "2nd_variable",
                "is_correct": True,
                "explanation": "Identifiers cannot start with a digit.",
            },
        ]
        
        save_quiz_attempt(
            user_id=user_id,
            topic_id=t1["id"],
            total_questions=5,
            correct_answers=5,
            score_percentage=100.0,
            responses=responses,
        )
        
        save_recommendation(
            user_id=user_id,
            topic_id=t1["id"],
            recommendation="Ready to Advance: Outstanding 100% score on Python Variables. Proceed to Day 2 Operators and Branching Logic.",
            recommendation_type="progression",
        )
        
    print(f"Demo data seeded successfully for user Alex Johnson (User ID: {user_id}, Plan ID: {plan_id})")

if __name__ == "__main__":
    seed_demo_data()
