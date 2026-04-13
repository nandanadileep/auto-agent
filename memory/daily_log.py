from datetime import datetime, timezone
from pathlib import Path

from config import DAILY_LOG_DIR


def _project_log_dir() -> Path:
    try:
        from state import get_active_project
        name = get_active_project().get("name", "default")
    except Exception:
        name = "default"
    return Path(DAILY_LOG_DIR) / name


def _log_path(now: datetime) -> Path:
    return _project_log_dir() / str(now.year) / f"{now.month:02d}" / f"{now.date().isoformat()}.md"


def write_to_daily_log(observation: str):
    try:
        now = datetime.now(timezone.utc)
        path = _log_path(now)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(f"- {now.strftime('%H:%M')} {observation}\n")
    except Exception as e:
        from actions import print_brief
        print_brief(f"Failed to write daily log: {e}")


def get_todays_log() -> str:
    try:
        path = _log_path(datetime.now(timezone.utc))
        if not path.exists():
            return ""
        return path.read_text()
    except Exception:
        return ""
