import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_AI_STUDIO_KEY = os.getenv("GOOGLE_AI_STUDIO_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
KAIROS_REPO_PATH = os.getenv("KAIROS_REPO_PATH", ".")

if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN is required but not set in .env")
if not GITHUB_REPO:
    raise EnvironmentError("GITHUB_REPO is required but not set in .env (format: username/reponame)")

TICK_INTERVAL_MINUTES = 5
TICK_TIMEOUT_SECONDS = 120
IDLE_THRESHOLD_SECONDS = 300
MEMORY_MD_PATH = "memory/MEMORY.md"
DAILY_LOG_DIR = "logs"
DB_PATH = "kairos.db"
MAX_CONTEXT_TOKENS = 2000
