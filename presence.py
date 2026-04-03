import re
import subprocess
from config import IDLE_THRESHOLD_SECONDS


def _get_idle_seconds() -> float:
    result = subprocess.run(
        ["ioreg", "-c", "IOHIDSystem"],
        capture_output=True, text=True, timeout=5
    )
    match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', result.stdout)
    if not match:
        raise ValueError("HIDIdleTime not found in ioreg output")
    nanoseconds = int(match.group(1))
    return nanoseconds / 1e9


def get_autonomy_level() -> str:
    try:
        idle = _get_idle_seconds()
    except Exception:
        return "low"

    if idle > IDLE_THRESHOLD_SECONDS:
        return "high"
    elif idle > 60:
        return "medium"
    else:
        return "low"
