from pathlib import Path

from config import MEMORY_MD_PATH

_BASE_MEMORY_DIR = Path(MEMORY_MD_PATH).parent


def _project_dir() -> Path:
    try:
        from state import get_active_project
        name = get_active_project().get("name", "default")
    except Exception:
        name = "default"
    return _BASE_MEMORY_DIR / "projects" / name


def _topics_dir() -> Path:
    return _project_dir() / "topics"


def _memory_md_path() -> Path:
    return _project_dir() / "MEMORY.md"


def read_memory_md() -> str:
    try:
        path = _memory_md_path()
        if not path.exists():
            return ""
        return path.read_text()
    except Exception:
        return ""


def write_memory_md(content: str):
    try:
        path = _memory_md_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = content.splitlines()
        if len(lines) > 200:
            content = "\n".join(lines[:200])
        path.write_text(content)
    except Exception as e:
        from actions import print_brief
        print_brief(f"Failed to write MEMORY.md: {e}")


def read_topic(topic: str) -> str:
    try:
        path = _topics_dir() / f"{topic}.md"
        if not path.exists():
            return ""
        return path.read_text()
    except Exception:
        return ""


def write_topic(topic: str, content: str):
    try:
        td = _topics_dir()
        td.mkdir(parents=True, exist_ok=True)
        path = td / f"{topic}.md"
        lines = content.splitlines()
        if len(lines) > 100:
            content = "\n".join(lines[:100])
        path.write_text(content)
    except Exception as e:
        from actions import print_brief
        print_brief(f"Failed to write topic {topic}: {e}")


def list_topics() -> list:
    try:
        td = _topics_dir()
        if not td.exists():
            return []
        return [p.stem for p in td.glob("*.md")]
    except Exception:
        return []


def read_all_topics() -> dict:
    return {topic: read_topic(topic) for topic in list_topics()}
