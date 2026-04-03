import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import tiktoken
from git import Repo, InvalidGitRepositoryError

from config import KAIROS_REPO_PATH, MAX_CONTEXT_TOKENS, MEMORY_MD_PATH

SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".venv"}


def _count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def _git_section(max_commits: int = 10) -> dict:
    try:
        repo = Repo(KAIROS_REPO_PATH)
        commits = list(repo.iter_commits(max_count=max_commits))
        history = [
            {
                "message": c.message.strip(),
                "author": c.author.name,
                "timestamp": datetime.fromtimestamp(c.committed_date, tz=timezone.utc).isoformat(),
            }
            for c in commits
        ]
        changed_files = set()
        for c in commits[:5]:
            if c.parents:
                diff = c.parents[0].diff(c)
                for d in diff:
                    changed_files.add(d.b_path or d.a_path)
        return {"history": history, "recently_changed_files": sorted(changed_files)}
    except Exception:
        return {"history": [], "recently_changed_files": []}


def _filesystem_section() -> dict:
    try:
        root = Path(KAIROS_REPO_PATH)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        modified_py = []
        todos = []

        for path in root.rglob("*.py"):
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if mtime > cutoff:
                    modified_py.append(str(path.relative_to(root)))

                for i, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
                    upper = line.upper()
                    if any(tag in upper for tag in ("TODO", "FIXME", "HACK")):
                        todos.append({
                            "file": str(path.relative_to(root)),
                            "line": i,
                            "text": line.strip(),
                        })
            except Exception:
                continue

        return {"modified_py_last_24h": modified_py, "todos": todos}
    except Exception:
        return {"modified_py_last_24h": [], "todos": []}


def _project_structure_section() -> dict:
    try:
        root = Path(KAIROS_REPO_PATH)

        readme_exists = (root / "README.md").exists()

        deps_content = ""
        for fname in ("requirements.txt", "pyproject.toml"):
            fpath = root / fname
            if fpath.exists():
                try:
                    deps_content = fpath.read_text(errors="ignore")
                except Exception:
                    pass
                break

        env_example_keys = set()
        env_keys = set()

        example_path = root / ".env.example"
        if example_path.exists():
            for line in example_path.read_text(errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    env_example_keys.add(line.split("=")[0].strip())

        env_path = root / ".env"
        if env_path.exists():
            for line in env_path.read_text(errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    env_keys.add(line.split("=")[0].strip())

        missing_env_keys = sorted(env_example_keys - env_keys)

        return {
            "readme_exists": readme_exists,
            "deps": deps_content,
            "missing_env_keys": missing_env_keys,
        }
    except Exception:
        return {"readme_exists": False, "deps": "", "missing_env_keys": []}


def _memory_section() -> str:
    try:
        path = Path(MEMORY_MD_PATH)
        if path.exists():
            return path.read_text(errors="ignore")
        return ""
    except Exception:
        return ""


async def build_context() -> dict:
    ctx = {
        "git": _git_section(max_commits=10),
        "filesystem": _filesystem_section(),
        "project": _project_structure_section(),
        "memory": _memory_section(),
    }

    if _count_tokens(str(ctx)) > MAX_CONTEXT_TOKENS:
        ctx["git"] = _git_section(max_commits=3)
        ctx["project"]["deps"] = ""

    return ctx
