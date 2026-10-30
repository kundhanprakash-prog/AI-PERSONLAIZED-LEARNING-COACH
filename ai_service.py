import os
import json
import logging
from typing import Dict, Any, List, Optional
from utils.config import get_gemini_api_key, DEFAULT_GEMINI_MODEL, FALLBACK_GEMINI_MODEL
from utils.helpers import safe_parse_json, get_performance_tier
from validators import validate_study_plan_structure, validate_quiz_structure

logger = logging.getLogger(__name__)

def _get_genai_client(api_key: Optional[str] = None):
    """Obtain an authenticated google.genai Client."""
    key = (api_key or get_gemini_api_key()).strip()
    if not key:
        raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in your .env or Settings page.")
    
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Google GenAI client: {str(e)}")

def _call_gemini_with_fallback(
    prompt: str,
    expect_json: bool = True,
    system_instruction: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    """
    Call Gemini API with model fallback and error handling.
    Tries the default model first, then the fallback model if needed.
    """
    client = _get_genai_client(api_key)
    from google.genai import types

    primary_model = model_name or DEFAULT_GEMINI_MODEL
    models_to_try = [primary_model]
    if FALLBACK_GEMINI_MODEL not in models_to_try:
        models_to_try.append(FALLBACK_GEMINI_MODEL)

    last_error = None
    for model in models_to_try:
        try:
            config_args = {"temperature": 0.4}
            if expect_json:
                config_args["response_mime_type"] = "application/json"
            if system_instruction:
                config_args["system_instruction"] = system_instruction

            config = types.GenerateContentConfig(**config_args)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                return response.text
            raise ValueError(f"Empty response returned from model {model}")
        except Exception as err:
            logger.warning(f"Gemini API call to {model} failed: {err}")
            last_error = err
            continue

    raise RuntimeError(f"All Gemini model attempts failed. Last error: {str(last_error)}")

# ----------------- 1. STUDY PLAN GENERATOR -----------------

def generate_study_plan(
    subject: str,
    learning_goal: str,
    current_level: str,
    target_duration: int,
    daily_study_time: int,
    approach: str = "",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a complete, personalized day-by-day study plan using Gemini.
    Validates output structure and ensures duration and daily times are respected.
    """
    prompt = f"""
You are a senior curriculum designer and AI learning coach.
Create an intensive, highly practical, day-by-day personalized learning plan.

Student Profile:
- Subject: {subject}
- Learning Goal: {learning_goal}
- Current Knowledge Level: {current_level}
- Target Duration: Exactly {target_duration} days
- Daily Available Study Time: {daily_study_time} minutes
- Learning Approach: {approach or 'Balanced Theory and Hands-on Application'}

Strict Requirements:
1. Generate EXACTLY {target_duration} days (numbered 1 to {target_duration}).
2. Calibrate difficulty to the '{current_level}' level.
3. Every day's estimated time MUST be approximately {daily_study_time} minutes.
4. Topics must be logically sequential, avoiding redundant repetitions.
5. Provide specific, actionable practice activities and real learning resources for each day.

Return your response in PURE JSON conforming EXACTLY to this schema:
{{
  "subject": "{subject}",
  "learning_goal": "{learning_goal}",
  "level": "{current_level}",
  "target_duration_days": {target_duration},
  "daily_study_time_minutes": {daily_study_time},
  "days": [
    {{
      "day_number": 1,
      "topic_name": "Clear descriptive topic name",
      "objectives": ["Specific objective 1", "Specific objective 2"],
      "subtopics": ["Subtopic A", "Subtopic B", "Subtopic C"],
      "estimated_time_minutes": {daily_study_time},
      "practice_activities": ["Concrete hands-on activity", "Challenge question"],
      "resources": ["Recommended documentation / tutorial reference", "Key concepts cheat-sheet"]
    }}
  ]
}}
"""
    system_inst = "You are an expert AI personalized learning coach. You only output valid JSON conforming strictly to the requested schema."

    try:
        raw_text = _call_gemini_with_fallback(
            prompt=prompt,
            expect_json=True,
            system_instruction=system_inst,
            api_key=api_key,
        )
        success, plan_json, err = safe_parse_json(raw_text)
        if not success:
            raise ValueError(f"Failed to parse AI response as JSON: {err}")

        valid, val_err = validate_study_plan_structure(plan_json)
        if not valid:
            raise ValueError(f"AI response did not match study plan schema: {val_err}")

        return plan_json

    except Exception as e:
        logger.error(f"Gemini study plan generation error: {e}")
        # Build a robust dynamic fallback curriculum if offline/error to maintain application flow
        return _build_fallback_study_plan(
            subject=subject,
            learning_goal=learning_goal,
            current_level=current_level,
            target_duration=target_duration,
            daily_study_time=daily_study_time,
            error_note=str(e),
        )

# ----------------- 2. QUIZ GENERATOR -----------------

def generate_quiz(
    topic_name: str,
    level: str = "Beginner",
    count: int = 5,
    subject: str = "",
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate multiple-choice quiz questions for a topic using Gemini.
    Returns a list of 5 question dicts.
    """
    prompt = f"""
You are an expert examiner in {subject or 'the field'} assessing: "{topic_name}".
Knowledge Level: {level}.

Create EXACTLY {count} challenging multiple-choice questions to test deep understanding of "{topic_name}".

For each question:
1. Provide a clear, realistic scenario or conceptual question text.
2. Provide EXACTLY 4 distinct answer options.
3. Specify the exact correct answer (must match one of the 4 options verbatim).
4. Provide a thorough pedagogical explanation for why the answer is correct and why other choices are misconceptions.
5. Indicate difficulty level (e.g. 'Easy', 'Medium', or 'Hard').
6. Reference the related subtopic.

Return your response in PURE JSON adhering to this schema:
{{
  "questions": [
    {{
      "question_text": "...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "...",
      "difficulty": "Medium",
      "related_topic": "{topic_name}"
    }}
  ]
}}
"""
    system_inst = "You are an expert assessment generator. Always return valid JSON containing questions list."

    try:
        raw_text = _call_gemini_with_fallback(
            prompt=prompt,
            expect_json=True,
            system_instruction=system_inst,
            api_key=api_key,
        )
        success, quiz_data, err = safe_parse_json(raw_text)
        if not success:
            raise ValueError(f"Failed to parse quiz JSON: {err}")

        valid, val_err = validate_quiz_structure(quiz_data)
        if not valid:
            raise ValueError(f"Quiz structure validation failed: {val_err}")

        questions = quiz_data.get("questions") if isinstance(quiz_data, dict) else quiz_data
        return questions

    except Exception as e:
        logger.error(f"Gemini quiz generation error: {e}")
        return _build_fallback_quiz(topic_name=topic_name, level=level, count=count, error_note=str(e))

# ----------------- 3. PERFORMANCE EVALUATION -----------------

def evaluate_learning_performance(
    score_percentage: float,
    correct_answers: int,
    total_questions: int,
    topic_name: str,
    incorrect_questions: Optional[List[Dict[str, Any]]] = None,
    history: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate quiz results and generate personalized coaching feedback using Gemini.
    Note: Python calculates the score; Gemini provides qualitative insights.
    """
    tier_info = get_performance_tier(score_percentage)
    attempts_count = len(history) if history else 1

    prompt = f"""
You are an empathetic, highly analytical AI study coach.
Evaluate this student's quiz attempt on the topic: "{topic_name}".

Student Performance Statistics (Calculated by Python):
- Score: {correct_answers}/{total_questions} ({score_percentage}%)
- Guidance Tier: {tier_info['label']} ({tier_info['tier']})
- Total Attempts on this topic: {attempts_count}

Incorrect Questions / Concepts Missed:
{json.dumps(incorrect_questions or [], indent=2)}

Coaching Instructions:
1. Give constructive, motivating feedback highlighting areas of strength and specific knowledge gaps.
2. If score is below 50%, be encouraging, diagnose foundational hurdles, and recommend revision.
3. If score is 50-69%, highlight specific concepts that need reinforcement.
4. If score is 70-84%, acknowledge good understanding while pointing out subtle distinctions.
5. If score is 85%+, recommend advancing or undertaking a mini-project.
6. CAUTION: Do NOT declare that the student has completely mastered the topic from one quiz; state that they have demonstrated strong understanding on this assessment.

Return PURE JSON:
{{
  "summary_feedback": "2-3 sentences of clear personalized feedback.",
  "strengths": ["Concept understood 1", "Concept understood 2"],
  "weak_areas": ["Concept needing revision 1", "Concept needing revision 2"],
  "suggested_actions": ["Concrete action 1", "Concrete action 2"]
}}
"""
    try:
        raw_text = _call_gemini_with_fallback(
            prompt=prompt,
            expect_json=True,
            api_key=api_key,
        )
        success, eval_data, _ = safe_parse_json(raw_text)
        if success and isinstance(eval_data, dict):
            eval_data["tier"] = tier_info
            return eval_data
    except Exception as e:
        logger.warning(f"Gemini performance evaluation fallback used: {e}")

    # Fallback qualitative feedback based on Python-calculated score
    if score_percentage < 50.0:
        return {
            "tier": tier_info,
            "summary_feedback": f"You scored {correct_answers} out of {total_questions} ({score_percentage}%) in {topic_name}. You should revise the fundamental principles and key terminology before attempting another practice quiz.",
            "strengths": ["Demonstrated willingness to test understanding and pinpoint gaps"],
            "weak_areas": [f"Core mechanics and definitions in {topic_name}", "Practical problem-solving scenarios"],
            "suggested_actions": ["Review topic learning notes and documentation", "Take a targeted revision quiz", "Work through simple step-by-step examples"],
        }
    elif score_percentage < 70.0:
        return {
            "tier": tier_info,
            "summary_feedback": f"You scored {correct_answers} out of {total_questions} ({score_percentage}%) in {topic_name}. You understand the foundational concepts, but additional practice will solidify your problem-solving accuracy.",
            "strengths": ["Good basic comprehension of the topic essentials"],
            "weak_areas": ["Handling edge cases and multi-step applications"],
            "suggested_actions": ["Review the explanations for the incorrect questions", "Re-attempt similar questions to build speed and accuracy"],
        }
    elif score_percentage < 85.0:
        return {
            "tier": tier_info,
            "summary_feedback": f"Great job! You scored {correct_answers} out of {total_questions} ({score_percentage}%) in {topic_name}. You have a solid grasp of this topic.",
            "strengths": ["Accurate understanding of majority of core topics and application rules"],
            "weak_areas": ["Minor nuances in complex or tricky scenarios"],
            "suggested_actions": ["Quickly review missed explanations", "Proceed to the next scheduled topic with confidence"],
        }
    else:
        return {
            "tier": tier_info,
            "summary_feedback": f"Outstanding result! You scored {correct_answers} out of {total_questions} ({score_percentage}%) in {topic_name}. You've demonstrated excellent understanding on this assessment.",
            "strengths": ["High accuracy", "Strong conceptual clarity and error-free problem analysis"],
            "weak_areas": [],
            "suggested_actions": ["Mark this topic as completed", "Move ahead to the next topic", "Try building a mini-project to apply this knowledge"],
        }

# ----------------- 4. ADAPTIVE RECOMMENDATIONS -----------------

def generate_learning_recommendations(
    score_percentage: float,
    topic_name: str,
    level: str = "Beginner",
    weak_concepts: Optional[List[str]] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate adaptive learning recommendations tailored to the student's performance tier:
    - LOW (<50%): revision, simpler breakdown, practice quiz
    - MEDIUM (50-69%): more practice, review mistakes, moderate questions
    - HIGH (>=85%): progression, advanced practice, mini-project
    """
    tier = get_performance_tier(score_percentage)["tier"]

    prompt = f"""
You are an adaptive recommendation engine for an AI learning platform.
Student scored {score_percentage}% (Tier: {tier}) on topic: "{topic_name}" (Level: {level}).
Weak concepts noted: {weak_concepts or []}.

Generate an adaptive recommendation plan based on this tier:
- If LOW: recommend revision, foundational breakdown, easier practice quiz.
- If MEDIUM: recommend targeted practice, reviewing mistakes, moderate-difficulty questions.
- If HIGH / GOOD: recommend moving to next topic, tackling advanced questions, and suggesting a mini-project.

Return PURE JSON:
{{
  "recommendation_type": "{'revision' if tier == 'LOW' else ('practice' if tier == 'MEDIUM' else 'progression')}",
  "recommendation_headline": "Short punchy recommendation title",
  "detailed_advice": "Detailed actionable coaching advice.",
  "recommended_next_step": "Exact next step for the student to take.",
  "mini_project_or_challenge": "A practical 15-minute challenge or mini-project applying {topic_name}."
}}
"""
    try:
        raw_text = _call_gemini_with_fallback(prompt=prompt, expect_json=True, api_key=api_key)
        success, rec_data, _ = safe_parse_json(raw_text)
        if success and isinstance(rec_data, dict):
            return rec_data
    except Exception as e:
        logger.warning(f"Gemini recommendation generation fallback: {e}")

    # Fallback adaptive recommendation
    if tier == "LOW":
        return {
            "recommendation_type": "revision",
            "recommendation_headline": f"Revise Core Concepts of {topic_name}",
            "detailed_advice": f"Your score ({score_percentage}%) indicates that several key concepts in {topic_name} require revision. We recommend you revise the daily subtopics and break down each concept into smaller parts.",
            "recommended_next_step": "Read the AI topic explanation below, review missed answers, and generate an easier practice quiz.",
            "mini_project_or_challenge": f"Write down 3 simple real-world examples or code snippets demonstrating {topic_name}.",
        }
    elif tier == "MEDIUM":
        return {
            "recommendation_type": "practice",
            "recommendation_headline": f"Reinforce Understanding with More Practice",
            "detailed_advice": f"You scored {score_percentage}%, showing fair familiarity with {topic_name}. With another round of practice focused on your missed questions, you'll reach top confidence.",
            "recommended_next_step": "Review the explanation for each question you missed, then generate a new set of practice questions.",
            "mini_project_or_challenge": f"Create a short script or problem-solving test case covering the trickiest part of {topic_name}.",
        }
    else:
        return {
            "recommendation_type": "progression",
            "recommendation_headline": f"Ready to Advance - Try a Mini-Project!",
            "detailed_advice": f"Excellent achievement with {score_percentage}%! You are ready to move on to the next scheduled study topic.",
            "recommended_next_step": "Mark this topic as completed and continue with Day's next topic.",
            "mini_project_or_challenge": f"Hands-on Mini-Project: Build a functional module incorporating {topic_name} with user input and validation.",
        }

# ----------------- 5. TOPIC EXPLANATION -----------------

def explain_topic(
    topic_name: str,
    subtopics: Optional[List[str]] = None,
    level: str = "Beginner",
    api_key: Optional[str] = None,
) -> str:
    """
    Generate a clear, beautifully structured markdown study guide for a topic.
    """
    subtopics_text = ", ".join(subtopics) if subtopics else "Key core principles"
    prompt = f"""
You are an expert tutor. Provide a comprehensive, easy-to-read, beautifully formatted study explanation for:
Topic: "{topic_name}"
Knowledge Level: {level}
Subtopics to cover: {subtopics_text}

Format the response using clean Markdown:
1. ## Overview & Why It Matters
2. ## Core Concepts Explained (use bullet points and clear analogies)
3. ## Practical Code or Scenario Example
4. ## Common Pitfalls & How to Avoid Them
5. ## Quick Self-Check Questions
"""
    try:
        raw_text = _call_gemini_with_fallback(
            prompt=prompt,
            expect_json=False,
            api_key=api_key,
        )
        if raw_text and len(raw_text.strip()) > 50:
            return raw_text.strip()
    except Exception as e:
        logger.warning(f"Gemini topic explanation fallback: {e}")

    # Fallback explanation
    return f"""## Overview: {topic_name}
This study module covers the core concepts and best practices of **{topic_name}** tailored for **{level}** learners.

### Key Objectives & Subtopics
- Subtopics: {subtopics_text}
- Focus on practical understanding, syntax rules, and error-free implementation.

### Practical Learning Advice
1. Break down the topic into bite-sized components.
2. Type out working examples manually rather than copying and pasting.
3. Test edge cases and observe any error messages to understand boundaries.
4. Take a practice quiz once you have finished reviewing the materials.
"""

# ----------------- DYNAMIC FALLBACK BUILDERS -----------------

def _build_fallback_study_plan(
    subject: str,
    learning_goal: str,
    current_level: str,
    target_duration: int,
    daily_study_time: int,
    error_note: str = "",
) -> Dict[str, Any]:
    """Generates an intelligent, high-quality structured curriculum dynamically."""
    days = []
    base_topics = [
        ("Foundations & Core Principles", "Introduction to core syntax, environment setup, and fundamental terminology"),
        ("Data Types, Variables & Operations", "Working with data types, manipulation, and conditional branching"),
        ("Control Flow & Iteration", "Loops, iteration patterns, and algorithmic flow controls"),
        ("Modular Functions & Architecture", "Writing reusable functions, parameter handling, and return values"),
        ("Collections & Data Structures", "Working with lists, dictionaries, mappings, and collection methods"),
        ("Error Handling & Clean Code", "Debugging techniques, try-catch blocks, and defensive programming"),
        ("Intermediate Logic & Algorithms", "Implementing problem-solving algorithms and state management"),
        ("Practical Project: Part 1", "Planning and starting the architecture for a hands-on application"),
        ("Practical Project: Part 2", "Implementing core business logic and testing user interactions"),
        ("Comprehensive Review & Assessment", "Consolidating all learned topics, reviewing weak areas, and final evaluation"),
    ]

    for day_i in range(1, target_duration + 1):
        topic_idx = (day_i - 1) % len(base_topics)
        cycle = ((day_i - 1) // len(base_topics)) + 1
        name, desc = base_topics[topic_idx]
        title = f"{subject}: {name}" if cycle == 1 else f"{subject}: {name} (Part {cycle})"

        days.append({
            "day_number": day_i,
            "topic_name": title,
            "objectives": [
                f"Master key concepts of {name.lower()} in {subject}",
                f"Apply {desc.lower()} to practical exercises",
                f"Demonstrate proficiency through targeted quiz assessments",
            ],
            "subtopics": [
                f"{name} syntax & concepts",
                f"Best practices for {current_level} level",
                f"Common patterns and practical edge cases",
            ],
            "estimated_time_minutes": daily_study_time,
            "practice_activities": [
                f"Implement 2 practical code exercises exploring {name}",
                f"Take the Day {day_i} MCQ practice quiz",
            ],
            "resources": [
                f"Official {subject} Documentation",
                f"{subject} {current_level} Reference Handbook",
            ],
        })

    return {
        "subject": subject,
        "learning_goal": learning_goal,
        "level": current_level,
        "target_duration_days": target_duration,
        "daily_study_time_minutes": daily_study_time,
        "days": days,
        "is_fallback": True,
        "api_notice": f"Plan generated via dynamic fallback engine ({error_note})" if error_note else None,
    }

def _build_fallback_quiz(
    topic_name: str,
    level: str = "Beginner",
    count: int = 5,
    error_note: str = "",
) -> List[Dict[str, Any]]:
    """Build a dynamically structured 5-question MCQ set when offline."""
    questions = [
        {
            "question_text": f"What is the primary objective of studying '{topic_name}' in this curriculum?",
            "options": [
                f"To establish foundational mastery and practical application of {topic_name}",
                "To memorize theoretical terminology without practical implementation",
                "To bypass standard programming workflows and data structures",
                "To replace all automated testing with manual inspection",
            ],
            "correct_answer": f"To establish foundational mastery and practical application of {topic_name}",
            "explanation": f"Understanding {topic_name} provides the foundational concepts required to build real-world, scalable applications.",
            "difficulty": "Easy",
            "related_topic": topic_name,
        },
        {
            "question_text": f"When implementing concepts related to '{topic_name}', which practice is considered industry standard?",
            "options": [
                "Writing clean, modular code with clear naming and input validation",
                "Writing all code in a single global script without functions or classes",
                "Ignoring error messages and disabling exception handlers",
                "Hardcoding variables and database queries directly in UI components",
            ],
            "correct_answer": "Writing clean, modular code with clear naming and input validation",
            "explanation": "Modularity, clear naming, and robust validation ensure code is maintainable, testable, and secure.",
            "difficulty": "Medium",
            "related_topic": topic_name,
        },
        {
            "question_text": f"Which of the following is a common pitfall when working with '{topic_name}'?",
            "options": [
                "Assuming initial assumptions hold true without verifying edge cases and boundary conditions",
                "Using version control and writing automated unit tests",
                "Structuring code with modular helper functions",
                "Reviewing official language documentation for updates",
            ],
            "correct_answer": "Assuming initial assumptions hold true without verifying edge cases and boundary conditions",
            "explanation": "Edge cases and boundary conditions frequently cause subtle runtime bugs if not explicitly tested.",
            "difficulty": "Medium",
            "related_topic": topic_name,
        },
        {
            "question_text": f"How should a student at the '{level}' level best verify their understanding of '{topic_name}'?",
            "options": [
                "By building a hands-on project and verifying answers through targeted assessments",
                "By exclusively reading theory without writing code",
                "By skipping practice exercises directly to final advanced examinations",
                "By using pre-built templates without understanding the underlying logic",
            ],
            "correct_answer": "By building a hands-on project and verifying answers through targeted assessments",
            "explanation": "Active recall, practical coding, and testing understanding through assessments yield the highest retention.",
            "difficulty": "Easy",
            "related_topic": topic_name,
        },
        {
            "question_text": f"What is the recommended next step after completing an assessment on '{topic_name}'?",
            "options": [
                "Review incorrect answers, reinforce weak areas, and proceed to the next milestone",
                "Immediately delete all study notes and previous project files",
                "Assume complete mastery regardless of the quiz score",
                "Never review the topic again",
            ],
            "correct_answer": "Review incorrect answers, reinforce weak areas, and proceed to the next milestone",
            "explanation": "Continuous feedback loops where you review misconceptions and solidify weak points are the core of mastery.",
            "difficulty": "Medium",
            "related_topic": topic_name,
        },
    ]
    return questions[:count]
