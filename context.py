import ast
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import tiktoken
from git import Repo, InvalidGitRepositoryError

from config import KAIROS_REPO_PATH, MAX_CONTEXT_TOKENS, MEMORY_MD_PATH, WATCHED_EXTENSIONS
from memory.memory_md import read_all_topics, read_memory_md

SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "dist", "build", ".next"}


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
        ext_set = set(WATCHED_EXTENSIONS)

        # comment markers per language family
        # hash-comment langs: py, rb, go, rs, sh
        # slash-comment langs: js, ts, tsx, jsx, cpp, c, java, go, rs
        # md is special — use <!-- or plain text TODOs
        HASH_EXTS  = {".py", ".rb", ".sh"}
        SLASH_EXTS = {".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".cpp", ".c", ".java"}
        MD_EXTS    = {".md"}

        modified_by_ext: dict[str, list[str]] = {}
        todos = []

        for path in root.rglob("*"):
            if path.suffix not in ext_set:
                continue
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            if not path.is_file():
                continue
            try:
                rel = str(path.relative_to(root))
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                if mtime > cutoff:
                    modified_by_ext.setdefault(path.suffix, []).append(rel)

                text = path.read_text(errors="ignore")
                ext = path.suffix
                for i, line in enumerate(text.splitlines(), start=1):
                    stripped = line.strip()
                    upper = stripped.upper()
                    found = False
                    if ext in HASH_EXTS:
                        found = stripped.startswith("#") and any(
                            upper.startswith(f"# {t}") or upper.startswith(f"#{t}")
                            for t in ("TODO", "FIXME", "HACK")
                        )
                    elif ext in SLASH_EXTS:
                        found = any(
                            upper.lstrip("/ ").startswith(t)
                            for t in ("TODO", "FIXME", "HACK")
                        ) and stripped.startswith(("//", "/*", "*"))
                    elif ext in MD_EXTS:
                        found = any(f"**{t}**" in upper or upper.startswith(t)
                                    for t in ("TODO", "FIXME", "HACK"))
                    if found:
                        todos.append({
                            "file": rel,
                            "line": i,
                            "text": stripped,
                        })
            except Exception:
                continue

        return {"modified_files_last_24h": modified_by_ext, "todos": todos}
    except Exception:
        return {"modified_files_last_24h": {}, "todos": []}


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
    import re as _re
    try:
        root = Path(KAIROS_REPO_PATH)
        dangling = []
        seen: set[tuple[str, str]] = set()

        def _add(file_rel: str, imp: str):
            key = (file_rel, imp)
            if key not in seen:
                seen.add(key)
                dangling.append({"file": file_rel, "import": imp})

        # ── Python: AST-based ──────────────────────────────────────────────
        existing_modules: set[str] = set()
        for p in root.rglob("*.py"):
            if any(skip in p.parts for skip in SKIP_DIRS):
                continue
            rel = p.relative_to(root)
            existing_modules.add(".".join(rel.with_suffix("").parts))
            existing_modules.add(rel.stem)

        local_roots: set[str] = set()
        for p in root.iterdir():
            if p.is_dir() and (p / "__init__.py").exists() and p.name not in SKIP_DIRS:
                local_roots.add(p.name)
            elif p.suffix == ".py" and p.name != "__init__.py":
                local_roots.add(p.stem)

        for path in root.rglob("*.py"):
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            try:
                tree = ast.parse(path.read_text(errors="ignore"))
            except Exception:
                continue
            file_rel = str(path.relative_to(root))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in local_roots and alias.name not in existing_modules:
                            _add(file_rel, alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        if top in local_roots and node.module not in existing_modules:
                            _add(file_rel, node.module)

        # ── JS/TS: relative import resolution ─────────────────────────────
        JS_TS_EXTS = {".js", ".ts", ".tsx", ".jsx"}
        # pattern: from './foo' or from '../bar/baz' — relative paths only
        IMPORT_RE = _re.compile(
            r"""(?:import\s.*?\bfrom\s+|require\s*\(\s*)['"](\.[^'"]+)['"]""",
            _re.MULTILINE,
        )
        JS_SUFFIXES = (".js", ".ts", ".tsx", ".jsx", ".json")

        for path in root.rglob("*"):
            if path.suffix not in JS_TS_EXTS:
                continue
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            if not path.is_file():
                continue
            try:
                text = path.read_text(errors="ignore")
            except Exception:
                continue
            file_rel = str(path.relative_to(root))
            for m in IMPORT_RE.finditer(text):
                specifier = m.group(1)
                # resolve relative to the importing file's directory
                candidate_base = (path.parent / specifier).resolve()
                # check if the file exists with any known suffix, or as a directory index
                exists = (
                    candidate_base.exists()  # exact match (e.g. foo.ts explicit)
                    or any((candidate_base.parent / (candidate_base.name + s)).exists()
                           for s in JS_SUFFIXES)
                    or any((candidate_base / ("index" + s)).exists()
                           for s in JS_SUFFIXES)
                )
                if not exists:
                    # keep specifier relative to repo root for readability
                    _add(file_rel, specifier)

        return dangling
    except Exception:
        return []


def _never_imported_section() -> list:
    try:
        root = Path(KAIROS_REPO_PATH)
        ENTRY_POINTS = {"main.py", "config.py", "setup.py", "conftest.py", "demo.py", "run_tests.py"}
        JS_TS_EXTS = {".js", ".ts", ".tsx", ".jsx"}
        JS_TS_ENTRY_STEMS = {"index", "main", "app", "server", "vite.config", "next.config",
                              "tailwind.config", "postcss.config", "jest.config", "webpack.config"}

        # ── Python: AST-based ──────────────────────────────────────────────
        all_py = [
            p for p in root.rglob("*.py")
            if not any(skip in p.parts for skip in SKIP_DIRS)
            and p.name != "__init__.py"
        ]

        imported_py = set()
        for path in all_py:
            try:
                tree = ast.parse(path.read_text(errors="ignore"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_py.add(alias.name.split(".")[0])
                            imported_py.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imported_py.add(node.module.split(".")[0])
                            imported_py.add(node.module)
            except Exception:
                continue

        never_imported = []
        for path in all_py:
            if path.name in ENTRY_POINTS:
                continue
            rel = path.relative_to(root)
            module_dotted = ".".join(rel.with_suffix("").parts)
            module_stem = path.stem
            if module_dotted not in imported_py and module_stem not in imported_py:
                never_imported.append(str(rel))

        # ── JS/TS: grep-based filename search ─────────────────────────────
        all_jsts = [
            p for p in root.rglob("*")
            if p.suffix in JS_TS_EXTS
            and not any(skip in p.parts for skip in SKIP_DIRS)
            and p.is_file()
        ]

        # build a corpus of all text to search for references
        all_jsts_text_parts: list[str] = []
        for path in all_jsts:
            try:
                all_jsts_text_parts.append(path.read_text(errors="ignore"))
            except Exception:
                pass
        jsts_corpus = "\n".join(all_jsts_text_parts)

        import re as _re
        for path in all_jsts:
            if path.stem in JS_TS_ENTRY_STEMS:
                continue
            stem = path.stem
            # look for any import referencing this filename (with or without extension)
            # e.g. from './utils/cache' or from '../cache' or from 'cache'
            pattern = _re.compile(
                r"""import\s.*?from\s+['"].*?""" + _re.escape(stem) + r"""['"]""",
                _re.DOTALL,
            )
            if not pattern.search(jsts_corpus):
                never_imported.append(str(path.relative_to(root)))

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
