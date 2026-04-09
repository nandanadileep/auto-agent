import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_AI_STUDIO_KEY = os.getenv("GOOGLE_AI_STUDIO_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
KAIROS_REPO_PATH = os.getenv("KAIROS_REPO_PATH", ".")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN is required but not set in .env")
if not GITHUB_REPO:
    raise EnvironmentError("GITHUB_REPO is required but not set in .env (format: username/reponame)")

WATCHED_EXTENSIONS = [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".cpp", ".java", ".rb"]

TICK_INTERVAL_MINUTES = 1 if DEMO_MODE else 5
TICK_TIMEOUT_SECONDS = 120
IDLE_THRESHOLD_SECONDS = 10 if DEMO_MODE else 300
MEMORY_MD_PATH = "memory/MEMORY.md"
DAILY_LOG_DIR = "logs"
DB_PATH = "kairos.db"
MAX_CONTEXT_TOKENS = 2000
VERBOSE_TICKS = DEMO_MODE
