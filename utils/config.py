import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "learning_coach.db"))

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_GEMINI_MODEL = "gemini-1.5-flash"

# Performance Guidance Thresholds (Configurable)
# Below 50%: Needs significant revision
# 50–69%: Needs additional practice
# 70–84%: Good understanding
# 85% and above: Ready to progress
SCORE_THRESHOLD_REVISION = 50.0
SCORE_THRESHOLD_PRACTICE = 70.0
SCORE_THRESHOLD_PROGRESS = 85.0

# Supported knowledge levels
KNOWLEDGE_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# Preferred learning approaches
LEARNING_APPROACHES = [
    "Concept First (Theory then Practice)",
    "Hands-on / Project-based",
    "Fast Track / Crash Course",
    "In-depth Comprehensive Mastery",
]

def get_gemini_api_key() -> str:
    """Retrieve the current Gemini API key from environment or os."""
    return os.getenv("GEMINI_API_KEY", "").strip()

def save_gemini_api_key(api_key: str):
    """Save the Gemini API key to .env and active environment."""
    clean_key = api_key.strip()
    os.environ["GEMINI_API_KEY"] = clean_key
    
    env_file = BASE_DIR / ".env"
    lines = []
    found = False
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={clean_key}\n")
                found = True
            else:
                new_lines.append(line)
        lines = new_lines
    
    if not found:
        lines.append(f"GEMINI_API_KEY={clean_key}\n")
        
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
