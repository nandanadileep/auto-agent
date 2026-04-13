import asyncio
import time

from watchfiles import awatch

from state import get_active_project

WATCH_EXTENSIONS = {".py", ".md", ".env", ".toml", ".txt"}
DEBOUNCE_SECONDS = 5


async def watch_and_tick():
    from daemon.tick import tick

    last_tick = 0.0
    watch_path = get_active_project().get("repo_path", ".")

    async for changes in awatch(watch_path):
        relevant = [
            (change, path) for change, path in changes
            if any(path.endswith(ext) for ext in WATCH_EXTENSIONS)
            and ".venv" not in path
            and "__pycache__" not in path
        ]

        if not relevant:
            continue

        now = time.monotonic()
        if now - last_tick < DEBOUNCE_SECONDS:
            continue

        last_tick = now
        await tick()
