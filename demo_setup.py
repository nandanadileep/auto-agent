import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from rich.console import Console

console = Console()

ROOT = Path(__file__).parent
DELAY = 2


def step(msg):
    console.print(f"[dim]→[/dim] {msg}")
    time.sleep(DELAY)


# 1. auth/login.py
step("creating auth/login.py with TODOs")
(ROOT / "auth").mkdir(exist_ok=True)
(ROOT / "auth" / "__init__.py").touch()
(ROOT / "auth" / "login.py").write_text("""\
# TODO: add rate limiting before prod
# TODO: log failed login attempts to audit trail
# TODO: replace hardcoded secret with env var

def login(username: str, password: str) -> bool:
    # stub — always returns True for now
    return True
""")

# 2. auth/session.py
step("creating auth/session.py with FIXME and HACK")
(ROOT / "auth" / "session.py").write_text("""\
# FIXME: sessions never expire — anyone who logs in stays logged in forever
# HACK: storing session tokens in memory, will not survive a restart

_sessions = {}

def create_session(user_id: str) -> str:
    token = f"tok_{user_id}_demo"
    _sessions[token] = user_id
    return token
""")

# 3. utils/cache.py — never imported anywhere
step("creating utils/cache.py (never imported anywhere)")
(ROOT / "utils").mkdir(exist_ok=True)
(ROOT / "utils" / "__init__.py").touch()
(ROOT / "utils" / "cache.py").write_text("""\
_cache = {}

def get(key: str):
    return _cache.get(key)

def set(key: str, value):
    _cache[key] = value
""")

# 4. dangling import in main.py
step("adding dangling import to main.py (utils.deleted_module)")
main_path = ROOT / "main.py"
original = main_path.read_text()
patched = original.replace(
    "import asyncio\nimport sys",
    "import asyncio\nimport sys\ntry:\n    from utils import deleted_module  # demo: dangling import\nexcept ImportError:\n    pass"
)
main_path.write_text(patched)

# 5. remove OLLAMA_BASE_URL from .env
step("removing OLLAMA_BASE_URL from .env (missing env key simulation)")
env_path = ROOT / ".env"
env_original = env_path.read_text()
env_patched = "\n".join(
    line for line in env_original.splitlines()
    if not line.startswith("OLLAMA_BASE_URL")
)
env_path.write_text(env_patched)

# 6. write fake daily log entries
step("writing 10 fake daily log entries across the day")
from config import DAILY_LOG_DIR
now = datetime.now(timezone.utc)
log_path = Path(DAILY_LOG_DIR) / str(now.year) / f"{now.month:02d}" / f"{now.date().isoformat()}.md"
log_path.parent.mkdir(parents=True, exist_ok=True)

observations = [
    "started working on auth module — login and session stubs created",
    "noticed session tokens stored in memory — will not survive restart",
    "PR #2 has been open for 7 days with no review — getting stale",
    "3 TODOs in auth/login.py — rate limiting and secret management missing",
    "utils/cache.py created but never imported anywhere",
    "test_auth.py references a deleted fixture — tests will fail on next run",
    "memory usage spiking during context build — might need to trim git history",
    "OLLAMA_BASE_URL missing from .env — ollama calls will fail silently",
    "dangling import in main.py: utils.deleted_module does not exist",
    "end of day — auth module incomplete, PR needs review, env config missing",
]

base_time = now.replace(hour=9, minute=0, second=0)
with log_path.open("a") as f:
    for i, obs in enumerate(observations):
        t = base_time + timedelta(hours=i * 0.8)
        f.write(f"- {t.strftime('%H:%M')} {obs}\n")

# summary
console.print("\n[bold green]demo setup complete[/bold green]\n")
console.print(f"  [dim]created[/dim]  auth/login.py — 3 TODOs")
console.print(f"  [dim]created[/dim]  auth/session.py — FIXME + HACK")
console.print(f"  [dim]created[/dim]  utils/cache.py — never imported")
console.print(f"  [dim]patched[/dim]  main.py — dangling import added")
console.print(f"  [dim]patched[/dim]  .env — OLLAMA_BASE_URL removed")
console.print(f"  [dim]written[/dim]  {log_path} — 10 entries")
console.print(f"\n  add DEMO_MODE=true to .env then run: python3 main.py")
