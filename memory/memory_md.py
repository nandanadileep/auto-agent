from pathlib import Path

from config import MEMORY_MD_PATH


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
