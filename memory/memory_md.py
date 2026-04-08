from pathlib import Path

from config import MEMORY_MD_PATH

TOPICS_DIR = Path(MEMORY_MD_PATH).parent / "topics"


def read_memory_md() -> str:
    try:
        path = Path(MEMORY_MD_PATH)
        if not path.exists():
            return ""
        return path.read_text()
    except Exception:
        return ""


def write_memory_md(content: str):
    try:
        path = Path(MEMORY_MD_PATH)
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
        path = TOPICS_DIR / f"{topic}.md"
        if not path.exists():
            return ""
        return path.read_text()
    except Exception:
        return ""


def write_topic(topic: str, content: str):
    try:
        TOPICS_DIR.mkdir(parents=True, exist_ok=True)
        path = TOPICS_DIR / f"{topic}.md"
        lines = content.splitlines()
        if len(lines) > 100:
            content = "\n".join(lines[:100])
        path.write_text(content)
    except Exception as e:
        from actions import print_brief
        print_brief(f"Failed to write topic {topic}: {e}")


def list_topics() -> list:
    try:
        if not TOPICS_DIR.exists():
            return []
        return [p.stem for p in TOPICS_DIR.glob("*.md")]
    except Exception:
        return []


def read_all_topics() -> dict:
    return {topic: read_topic(topic) for topic in list_topics()}
