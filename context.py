import ast
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import tiktoken
from git import Repo, InvalidGitRepositoryError

from config import KAIROS_REPO_PATH, MAX_CONTEXT_TOKENS, MEMORY_MD_PATH
from memory.memory_md import read_all_topics, read_memory_md

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
                    stripped = line.strip()
                    upper = stripped.upper()
                    if stripped.startswith("#") and any(upper.startswith(f"# {tag}") or upper.startswith(f"#{tag}") for tag in ("TODO", "FIXME", "HACK")):
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


def _dangling_imports_section() -> list:
    try:
        root = Path(KAIROS_REPO_PATH)

        # build set of all local module dotted names that actually exist
        existing_modules = set()
        for p in root.rglob("*.py"):
            if any(skip in p.parts for skip in SKIP_DIRS):
                continue
            rel = p.relative_to(root)
            existing_modules.add(".".join(rel.with_suffix("").parts))  # e.g. memory.daily_log
            existing_modules.add(rel.stem)                              # e.g. daily_log

        # local top-level packages/modules (dirs with __init__.py or root .py files)
        local_roots = set()
        for p in root.iterdir():
            if p.is_dir() and (p / "__init__.py").exists() and p.name not in SKIP_DIRS:
                local_roots.add(p.name)
            elif p.suffix == ".py" and p.name != "__init__.py":
                local_roots.add(p.stem)

        dangling = []
        all_py = [
            p for p in root.rglob("*.py")
            if not any(skip in p.parts for skip in SKIP_DIRS)
        ]

        for path in all_py:
            try:
                tree = ast.parse(path.read_text(errors="ignore"))
            except Exception:
                continue

            for node in ast.walk(tree):
                module = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in local_roots and alias.name not in existing_modules:
                            dangling.append({
                                "file": str(path.relative_to(root)),
                                "import": alias.name,
                            })
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        if top in local_roots and node.module not in existing_modules:
                            dangling.append({
                                "file": str(path.relative_to(root)),
                                "import": node.module,
                            })

        # deduplicate
        seen = set()
        result = []
        for d in dangling:
            key = (d["file"], d["import"])
            if key not in seen:
                seen.add(key)
                result.append(d)

        return result
    except Exception:
        return []


def _never_imported_section() -> list:
    try:
        root = Path(KAIROS_REPO_PATH)
        ENTRY_POINTS = {"main.py", "config.py", "setup.py", "conftest.py", "demo.py", "run_tests.py"}

        all_py = [
            p for p in root.rglob("*.py")
            if not any(skip in p.parts for skip in SKIP_DIRS)
            and p.name != "__init__.py"
        ]

        # collect all imported module names across the entire codebase (including entry points)
        imported = set()
        for path in all_py:
            try:
                tree = ast.parse(path.read_text(errors="ignore"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported.add(alias.name.split(".")[0])
                            imported.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imported.add(node.module.split(".")[0])
                            imported.add(node.module)
            except Exception:
                continue

        # check which non-entry-point files are never referenced
        never_imported = []
        for path in all_py:
            if path.name in ENTRY_POINTS:
                continue
            rel = path.relative_to(root)
            # build both dotted module name and stem
            module_dotted = ".".join(rel.with_suffix("").parts)
            module_stem = path.stem
            if module_dotted not in imported and module_stem not in imported:
                never_imported.append(str(rel))

        return sorted(never_imported)
    except Exception:
        return []


def _memory_section() -> dict:
    try:
        topics = read_all_topics()
        if topics:
            return topics
        # fallback to flat MEMORY.md if no topics yet
        flat = read_memory_md()
        return {"memory": flat} if flat else {}
    except Exception:
        return {}


async def build_context() -> dict:
    ctx = {
        "git": _git_section(max_commits=10),
        "filesystem": _filesystem_section(),
        "never_imported": _never_imported_section(),
        "dangling_imports": _dangling_imports_section(),
        "project": _project_structure_section(),
        "memory": _memory_section(),
    }

    if _count_tokens(str(ctx)) > MAX_CONTEXT_TOKENS:
        ctx["git"] = _git_section(max_commits=3)
        ctx["project"]["deps"] = ""

    return ctx
