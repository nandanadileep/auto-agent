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
    columns = [col[0] for col in db.execute("PRAGMA table_info(actions)").fetchall()]
    return [dict(zip(columns, row)) for row in rows]
