import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from utils.config import DATABASE_PATH

logger = logging.getLogger(__name__)

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Establish and return a SQLite database connection with row factory enabled
    and foreign key constraints enforced.
    """
    path = db_path or DATABASE_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite database schema with all required tables and indexes.
    """
    conn = get_connection(db_path)
    try:
        with conn:
            # 1. users
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. learner_profiles
            conn.execute("""
            CREATE TABLE IF NOT EXISTS learner_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                learning_goal TEXT NOT NULL,
                current_level TEXT NOT NULL,
                target_duration INTEGER NOT NULL,
                daily_study_time INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """)

            # 3. study_plans
            conn.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                learning_goal TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """)

            # 4. study_topics
            conn.execute("""
            CREATE TABLE IF NOT EXISTS study_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                day_number INTEGER NOT NULL,
                topic_name TEXT NOT NULL,
                objectives TEXT,
                estimated_time INTEGER,
                status TEXT DEFAULT 'pending',
                completed_at TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES study_plans (id) ON DELETE CASCADE
            );
            """)

            # 5. quiz_attempts
            conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_answers INTEGER NOT NULL,
                score_percentage REAL NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES study_topics (id) ON DELETE CASCADE
            );
            """)

            # 6. quiz_responses
            conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                selected_answer TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                explanation TEXT,
                FOREIGN KEY (attempt_id) REFERENCES quiz_attempts (id) ON DELETE CASCADE
            );
            """)

            # 7. learning_recommendations
            conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic_id INTEGER,
                recommendation TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES study_topics (id) ON DELETE SET NULL
            );
            """)
    finally:
        conn.close()

# ----------------- USERS & PROFILES -----------------

def get_or_create_user(name: str, db_path: Optional[str] = None) -> int:
    """Get an existing user by name or create a new one."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(?)", (name.strip(),))
            row = cursor.fetchone()
            if row:
                return row["id"]
            cursor = conn.execute("INSERT INTO users (name) VALUES (?)", (name.strip(),))
            return cursor.lastrowid
    finally:
        conn.close()

def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user details by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def list_all_users(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all registered users."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def save_learner_profile(
    user_id: int,
    subject: str,
    learning_goal: str,
    current_level: str,
    target_duration: int,
    daily_study_time: int,
    db_path: Optional[str] = None,
) -> int:
    """Store learner profile in database."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO learner_profiles (
                    user_id, subject, learning_goal, current_level, target_duration, daily_study_time
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, subject.strip(), learning_goal.strip(), current_level, target_duration, daily_study_time),
            )
            return cursor.lastrowid
    finally:
        conn.close()

def get_latest_profile(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent learner profile for a given user."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM learner_profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# ----------------- STUDY PLANS & TOPICS -----------------

def save_study_plan(
    user_id: int,
    subject: str,
    learning_goal: str,
    plan_dict: Dict[str, Any],
    db_path: Optional[str] = None,
) -> int:
    """Save generated study plan and all associated daily topics atomically."""
    conn = get_connection(db_path)
    try:
        with conn:
            plan_json_str = json.dumps(plan_dict, ensure_ascii=False)
            cursor = conn.execute(
                """
                INSERT INTO study_plans (user_id, subject, learning_goal, plan_json, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (user_id, subject.strip(), learning_goal.strip(), plan_json_str),
            )
            plan_id = cursor.lastrowid

            days = plan_dict.get("days", [])
            for day in days:
                day_num = day.get("day_number", 1)
                topic_name = day.get("topic_name", "Untitled Topic")
                objectives_raw = day.get("objectives", [])
                objectives_str = (
                    json.dumps(objectives_raw)
                    if isinstance(objectives_raw, list)
                    else str(objectives_raw)
                )
                est_time = day.get("estimated_time_minutes", 45)

                conn.execute(
                    """
                    INSERT INTO study_topics (
                        plan_id, day_number, topic_name, objectives, estimated_time, status
                    ) VALUES (?, ?, ?, ?, ?, 'pending')
                    """,
                    (plan_id, day_num, topic_name, objectives_str, est_time),
                )
            return plan_id
    finally:
        conn.close()

def get_study_plan(plan_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve study plan by ID with parsed plan_json."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM study_plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data["plan_data"] = json.loads(data["plan_json"])
        except Exception:
            data["plan_data"] = {}
        return data
    finally:
        conn.close()

def get_user_study_plans(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all study plans for a user."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM study_plans WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        plans = []
        for row in cursor.fetchall():
            d = dict(row)
            try:
                d["plan_data"] = json.loads(d["plan_json"])
            except Exception:
                d["plan_data"] = {}
            plans.append(d)
        return plans
    finally:
        conn.close()

def get_plan_topics(plan_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all topics for a study plan ordered by day number."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM study_topics WHERE plan_id = ? ORDER BY day_number ASC",
            (plan_id,),
        )
        topics = []
        for row in cursor.fetchall():
            item = dict(row)
            try:
                item["objectives_list"] = json.loads(item["objectives"])
            except Exception:
                item["objectives_list"] = [item["objectives"]] if item["objectives"] else []
            topics.append(item)
        return topics
    finally:
        conn.close()

def get_topic_by_id(topic_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single topic by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM study_topics WHERE id = ?", (topic_id,))
        row = cursor.fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["objectives_list"] = json.loads(item["objectives"])
        except Exception:
            item["objectives_list"] = [item["objectives"]] if item["objectives"] else []
        return item
    finally:
        conn.close()

def update_topic_status(
    topic_id: int,
    status: str,
    db_path: Optional[str] = None,
) -> bool:
    """Update topic completion status (e.g. 'completed' or 'pending')."""
    conn = get_connection(db_path)
    try:
        with conn:
            completed_at = datetime.now(timezone.utc).isoformat() if status == "completed" else None
            cursor = conn.execute(
                """
                UPDATE study_topics 
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, completed_at, topic_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()

# ----------------- QUIZ ATTEMPTS & RESPONSES -----------------

def save_quiz_attempt(
    user_id: int,
    topic_id: int,
    total_questions: int,
    correct_answers: int,
    score_percentage: float,
    responses: List[Dict[str, Any]],
    db_path: Optional[str] = None,
) -> int:
    """Save quiz attempt along with each question response."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO quiz_attempts (
                    user_id, topic_id, total_questions, correct_answers, score_percentage
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, topic_id, total_questions, correct_answers, score_percentage),
            )
            attempt_id = cursor.lastrowid

            for resp in responses:
                conn.execute(
                    """
                    INSERT INTO quiz_responses (
                        attempt_id, question_text, selected_answer, correct_answer, is_correct, explanation
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attempt_id,
                        resp.get("question_text", ""),
                        resp.get("selected_answer", ""),
                        resp.get("correct_answer", ""),
                        1 if resp.get("is_correct") else 0,
                        resp.get("explanation", ""),
                    ),
                )
            return attempt_id
    finally:
        conn.close()

def get_quiz_attempts_for_user(
    user_id: int,
    topic_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve quiz attempts for a user, optionally filtered by topic."""
    conn = get_connection(db_path)
    try:
        if topic_id:
            cursor = conn.execute(
                """
                SELECT qa.*, st.topic_name, st.day_number, sp.subject
                FROM quiz_attempts qa
                JOIN study_topics st ON qa.topic_id = st.id
                JOIN study_plans sp ON st.plan_id = sp.id
                WHERE qa.user_id = ? AND qa.topic_id = ?
                ORDER BY qa.submitted_at DESC, qa.id DESC
                """,
                (user_id, topic_id),
            )
        else:
            cursor = conn.execute(
                """
                SELECT qa.*, st.topic_name, st.day_number, sp.subject
                FROM quiz_attempts qa
                JOIN study_topics st ON qa.topic_id = st.id
                JOIN study_plans sp ON st.plan_id = sp.id
                WHERE qa.user_id = ?
                ORDER BY qa.submitted_at DESC, qa.id DESC
                """,
                (user_id,),
            )

        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_attempt_responses(attempt_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve detailed question responses for a given quiz attempt."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM quiz_responses WHERE attempt_id = ? ORDER BY id ASC",
            (attempt_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

# ----------------- LEARNING RECOMMENDATIONS -----------------

def save_recommendation(
    user_id: int,
    topic_id: Optional[int],
    recommendation: str,
    recommendation_type: str,
    db_path: Optional[str] = None,
) -> int:
    """Store generated recommendation."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO learning_recommendations (
                    user_id, topic_id, recommendation, recommendation_type
                ) VALUES (?, ?, ?, ?)
                """,
                (user_id, topic_id, recommendation.strip(), recommendation_type.strip()),
            )
            return cursor.lastrowid
    finally:
        conn.close()

def get_user_recommendations(
    user_id: int,
    limit: int = 10,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch recommendations for a user."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT lr.*, st.topic_name
            FROM learning_recommendations lr
            LEFT JOIN study_topics st ON lr.topic_id = st.id
            WHERE lr.user_id = ?
            ORDER BY lr.created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
