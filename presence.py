import platform
import re
import subprocess

from config import IDLE_THRESHOLD_SECONDS


def _idle_mac() -> float:
    result = subprocess.run(
        ["ioreg", "-c", "IOHIDSystem"],
        capture_output=True, text=True, timeout=5
    )
    match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', result.stdout)
    if not match:
        raise ValueError("HIDIdleTime not found in ioreg output")
    return int(match.group(1)) / 1e9


def _idle_windows() -> float:
    import ctypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        raise OSError("GetLastInputInfo failed")
    idle_ms = ctypes.windll.kernel32.GetTickCount() - info.dwTime
    return idle_ms / 1000.0


def _idle_linux() -> float:
    result = subprocess.run(
        ["xprintidle"],
        capture_output=True, text=True, timeout=5
    )
    if result.returncode != 0:
        raise OSError("xprintidle failed — is it installed?")
    return int(result.stdout.strip()) / 1000.0


def _get_idle_seconds() -> float:
    system = platform.system()
    if system == "Darwin":
        return _idle_mac()
    elif system == "Windows":
        return _idle_windows()
    elif system == "Linux":
        return _idle_linux()
    else:
        raise OSError(f"Unsupported platform: {system}")


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
