from datetime import datetime, timezone
import sqlite_utils
from config import DB_PATH

def _db():
    db = sqlite_utils.Database(DB_PATH)
    if "actions" not in db.table_names():
        db["actions"].create({
            "id": int,
            "timestamp": str,
            "action": str,
            "pr_id": int,
        }, pk="id", not_null={"timestamp", "action"})
    return db


def log_action(action: str, pr_id: int = None):
    _db()["actions"].insert({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "pr_id": pr_id,
    })


def already_notified_today(action: str) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    db = _db()
    rows = list(db.execute(
        "SELECT 1 FROM actions WHERE action = ? AND DATE(timestamp) = ? LIMIT 1",
        [action, today]
    ))
    return len(rows) > 0


def get_todays_actions() -> list:
    today = datetime.now(timezone.utc).date().isoformat()
    db = _db()
    rows = list(db.execute(
        "SELECT * FROM actions WHERE DATE(timestamp) = ? ORDER BY timestamp ASC",
        [today]
    ))
    columns = [col[1] for col in db.execute("PRAGMA table_info(actions)").fetchall()]
    return [dict(zip(columns, row)) for row in rows]


def _ensure_meta(db):
    if "meta" not in db.table_names():
        db["meta"].create({"key": str, "value": str}, pk="key")


def log_last_tick():
    db = _db()
    _ensure_meta(db)
    db["meta"].upsert({"key": "last_tick", "value": datetime.now(timezone.utc).isoformat()}, pk="key")


def get_last_tick() -> str:
    db = _db()
    _ensure_meta(db)
    try:
        row = db["meta"].get("last_tick")
        return row["value"]
    except Exception:
        return ""


def get_recent_actions(n: int = 10) -> list:
    db = _db()
    rows = list(db.execute(
        "SELECT * FROM actions ORDER BY timestamp DESC LIMIT ?",
        [n]
    ))
    columns = [col[1] for col in db.execute("PRAGMA table_info(actions)").fetchall()]
    return [dict(zip(columns, row)) for row in rows]


def get_actions_today_count() -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    db = _db()
    rows = list(db.execute(
        "SELECT COUNT(*) FROM actions WHERE DATE(timestamp) = ?",
        [today]
    ))
    return rows[0][0] if rows else 0


def log_last_dream():
    db = _db()
    _ensure_meta(db)
    db["meta"].upsert({"key": "last_dream", "value": datetime.now(timezone.utc).isoformat()}, pk="key")


def get_last_dream() -> str:
    db = _db()
    _ensure_meta(db)
    try:
        row = db["meta"].get("last_dream")
        return row["value"]
    except Exception:
        return ""
