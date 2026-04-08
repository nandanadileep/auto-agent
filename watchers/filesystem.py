import asyncio
import time

from watchfiles import awatch

from config import KAIROS_REPO_PATH

WATCH_EXTENSIONS = {".py", ".md", ".env", ".toml", ".txt"}
DEBOUNCE_SECONDS = 5


async def watch_and_tick():
    from daemon.tick import tick

    last_tick = 0.0

    async for changes in awatch(KAIROS_REPO_PATH):
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
