import json
from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils
from config import DB_PATH

_PROJECTS_JSON = Path(__file__).parent / "projects.json"


def _load_projects() -> list:
    try:
        return json.loads(_PROJECTS_JSON.read_text())
    except Exception:
        return []


def get_active_project() -> dict:
    db = _db()
    _ensure_meta(db)
    try:
        row = db["meta"].get("active_project")
        name = row["value"]
        projects = _load_projects()
        for p in projects:
            if p["name"] == name:
                return p
    except Exception:
        pass
    # default to first project
    projects = _load_projects()
    return projects[0] if projects else {}


def set_active_project(name: str) -> bool:
    projects = _load_projects()
    names = [p["name"] for p in projects]
    if name not in names:
        return False
    db = _db()
    _ensure_meta(db)
    db["meta"].upsert({"key": "active_project", "value": name}, pk="key")
    return True


def list_projects() -> list:
    return _load_projects()

def _db():
    db = sqlite_utils.Database(DB_PATH)
    if "actions" not in db.table_names():
        db["actions"].create({
            "id": int,
            "timestamp": str,
            "action": str,
            "pr_id": int,
            "project": str,
        }, pk="id", not_null={"timestamp", "action"})
    else:
        # migrate: add project column if missing
        cols = {col[1] for col in db.execute("PRAGMA table_info(actions)").fetchall()}
        if "project" not in cols:
            db.execute("ALTER TABLE actions ADD COLUMN project TEXT DEFAULT ''")
    return db


def _active_project_name() -> str:
    return get_active_project().get("name", "")


def log_action(action: str, pr_id: int = None):
    _db()["actions"].insert({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "pr_id": pr_id,
        "project": _active_project_name(),
    })


def already_notified_today(action: str) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    project = _active_project_name()
    db = _db()
    rows = list(db.execute(
        "SELECT 1 FROM actions WHERE action = ? AND DATE(timestamp) = ? AND project = ? LIMIT 1",
        [action, today, project]
    ))
    return len(rows) > 0


def get_todays_actions() -> list:
    today = datetime.now(timezone.utc).date().isoformat()
    project = _active_project_name()
    db = _db()
    rows = list(db.execute(
        "SELECT * FROM actions WHERE DATE(timestamp) = ? AND project = ? ORDER BY timestamp ASC",
        [today, project]
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
    project = _active_project_name()
    db = _db()
    rows = list(db.execute(
        "SELECT * FROM actions WHERE project = ? ORDER BY timestamp DESC LIMIT ?",
        [project, n]
    ))
    columns = [col[1] for col in db.execute("PRAGMA table_info(actions)").fetchall()]
    return [dict(zip(columns, row)) for row in rows]


def get_actions_today_count() -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    project = _active_project_name()
    db = _db()
    rows = list(db.execute(
        "SELECT COUNT(*) FROM actions WHERE DATE(timestamp) = ? AND project = ?",
        [today, project]
    ))
    return rows[0][0] if rows else 0


def get_context_hash() -> str:
    db = _db()
    _ensure_meta(db)
    try:
        key = f"context_hash:{_active_project_name()}"
        row = db["meta"].get(key)
        return row["value"]
    except Exception:
        return ""


def set_context_hash(h: str):
    db = _db()
    _ensure_meta(db)
    key = f"context_hash:{_active_project_name()}"
    db["meta"].upsert({"key": key, "value": h}, pk="key")


def log_last_dream():
    db = _db()
    _ensure_meta(db)
    key = f"last_dream:{_active_project_name()}"
    db["meta"].upsert({"key": key, "value": datetime.now(timezone.utc).isoformat()}, pk="key")


def get_last_dream() -> str:
    db = _db()
    _ensure_meta(db)
    try:
        key = f"last_dream:{_active_project_name()}"
        row = db["meta"].get(key)
        return row["value"]
    except Exception:
        return ""
