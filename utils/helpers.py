import re
import json
from datetime import datetime
from typing import Dict, Any, Tuple
from utils.config import (
    SCORE_THRESHOLD_REVISION,
    SCORE_THRESHOLD_PRACTICE,
    SCORE_THRESHOLD_PROGRESS,
)

def clean_json_string(text: str) -> str:
    """Extract and clean raw JSON from markdown or raw text output."""
    if not text:
        return ""
    # Strip markdown backticks block
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return text

def safe_parse_json(text: str) -> Tuple[bool, Any, str]:
    """
    Safely parse JSON string.
    Returns (success: bool, parsed_data: Any, error_message: str)
    """
    cleaned = clean_json_string(text)
    if not cleaned:
        return False, None, "Empty response received."
    try:
        data = json.loads(cleaned)
        return True, data, ""
    except json.JSONDecodeError as e:
        return False, None, f"JSON decoding failed: {str(e)}"

def calculate_score(correct: int, total: int) -> Tuple[int, int, float]:
    """
    Scoring rule: Python calculates score independently of Gemini.
    Returns (correct, total, percentage)
    """
    if total <= 0:
        return 0, 0, 0.0
    safe_correct = max(0, min(correct, total))
    percentage = round((safe_correct / total) * 100.0, 1)
    return safe_correct, total, percentage

def get_performance_tier(score_percentage: float) -> Dict[str, Any]:
    """
    Categorize score based on project performance thresholds:
    - Below 50%: Needs significant revision (Low)
    - 50–69%: Needs additional practice (Medium-Low)
    - 70–84%: Good understanding (Medium-High)
    - 85% and above: Ready to progress (High)
    """
    if score_percentage < SCORE_THRESHOLD_REVISION:
        return {
            "tier": "LOW",
            "label": "Needs Significant Revision",
            "color": "#ef4444",
            "badge": "🔴 Needs Revision",
            "summary": "Key foundational concepts need to be revisited and reinforced.",
            "next_action": "Revise the concepts, review mistakes, and retake the practice quiz.",
        }
    elif score_percentage < SCORE_THRESHOLD_PRACTICE:
        return {
            "tier": "MEDIUM",
            "label": "Needs Additional Practice",
            "color": "#f59e0b",
            "badge": "🟡 Needs Practice",
            "summary": "Basic concepts are understood, but further practice is needed for mastery.",
            "next_action": "Review incorrect answers and solve moderate-difficulty practice questions.",
        }
    elif score_percentage < SCORE_THRESHOLD_PROGRESS:
        return {
            "tier": "GOOD",
            "label": "Good Understanding",
            "color": "#3b82f6",
            "badge": "🔵 Good Understanding",
            "summary": "Solid grasp of core principles with minor knowledge gaps.",
            "next_action": "Consolidate learning with quick revision before moving forward.",
        }
    else:
        return {
            "tier": "HIGH",
            "label": "Ready to Progress",
            "color": "#10b981",
            "badge": "🟢 Ready to Progress",
            "summary": "Strong performance across tested concepts. Ready for higher-level topics.",
            "next_action": "Advance to the next day's topic or tackle a hands-on mini project.",
        }

def format_timestamp(ts_string: str) -> str:
    """Format an ISO timestamp to human-readable form."""
    if not ts_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts_string)
        return dt.strftime("%b %d, %Y - %I:%M %p")
    except Exception:
        return ts_string
