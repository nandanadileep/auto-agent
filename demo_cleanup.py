import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

console = Console()

ROOT = Path(__file__).parent
DELAY = 2


def step(msg):
    console.print(f"[dim]→[/dim] {msg}")
    time.sleep(DELAY)


# 1. remove auth/
step("removing auth/ directory")
auth_dir = ROOT / "auth"
if auth_dir.exists():
    shutil.rmtree(auth_dir)
    console.print("  [dim]deleted auth/[/dim]")
else:
    console.print("  [dim]auth/ not found — skipping[/dim]")

# 2. remove utils/cache.py and utils/__init__.py (only if created by demo)
step("removing utils/cache.py and utils/__init__.py")
cache_file = ROOT / "utils" / "cache.py"
utils_init = ROOT / "utils" / "__init__.py"
for f in (cache_file, utils_init):
    if f.exists():
        f.unlink()
        console.print(f"  [dim]deleted {f.relative_to(ROOT)}[/dim]")
utils_dir = ROOT / "utils"
if utils_dir.exists() and not any(utils_dir.iterdir()):
    utils_dir.rmdir()
    console.print("  [dim]deleted utils/ (now empty)[/dim]")

# 3. remove dangling import from main.py
step("restoring main.py — removing dangling import")
main_path = ROOT / "main.py"
if main_path.exists():
    original = main_path.read_text()
    patched = original.replace(
        "\ntry:\n    from utils import deleted_module  # demo: dangling import\nexcept ImportError:\n    pass",
        "",
    )
    if patched != original:
        main_path.write_text(patched)
        console.print("  [dim]dangling import removed from main.py[/dim]")
    else:
        console.print("  [dim]dangling import not found in main.py — skipping[/dim]")

# 4. restore OLLAMA_BASE_URL in .env
step("restoring OLLAMA_BASE_URL in .env")
env_path = ROOT / ".env"
if env_path.exists():
    env_text = env_path.read_text()
    if "OLLAMA_BASE_URL" not in env_text:
        env_path.write_text(env_text.rstrip("\n") + "\nOLLAMA_BASE_URL=http://localhost:11434\n")
        console.print("  [dim]OLLAMA_BASE_URL restored[/dim]")
    else:
        console.print("  [dim]OLLAMA_BASE_URL already present — skipping[/dim]")

# 5. clear today's log
step("clearing today's log file")
from config import DAILY_LOG_DIR
now = datetime.now(timezone.utc)
log_path = Path(DAILY_LOG_DIR) / str(now.year) / f"{now.month:02d}" / f"{now.date().isoformat()}.md"
if log_path.exists():
    log_path.unlink()
    console.print(f"  [dim]deleted {log_path}[/dim]")
else:
    console.print(f"  [dim]{log_path} not found — skipping[/dim]")

console.print("\n[bold green]demo cleanup complete[/bold green] — repo restored to pre-demo state\n")
