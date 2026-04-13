import asyncio
import hashlib
import json

from rich.console import Console

import config
from actions import notify, post_pr_comment, print_brief
from agent.llm import ask_tick_model
from context import build_context
from memory.daily_log import write_to_daily_log
from presence import get_autonomy_level
from state import already_notified_today, get_context_hash, log_action, log_last_tick, set_context_hash
from watchers.github import get_open_prs


def _compute_context_hash(ctx: dict, open_prs: list) -> str:
    git_history = ctx.get("git", {}).get("history", [])
    latest_commit = git_history[0].get("message", "") if git_history else ""
    stable = {
        "latest_commit": latest_commit,
        "prs": sorted(
            [(p["number"], p["review_status"], p["is_stale"]) for p in open_prs]
        ),
        "todos": ctx.get("filesystem", {}).get("todos", []),
        "never_imported": sorted(ctx.get("never_imported", [])),
        "dangling_imports": sorted(
            f"{d['file']}:{d['import']}" for d in ctx.get("dangling_imports", [])
        ),
    }
    return hashlib.md5(json.dumps(stable, sort_keys=True).encode()).hexdigest()

console = Console()


async def tick():
    log_last_tick()
    try:
        async with asyncio.timeout(config.TICK_TIMEOUT_SECONDS):
            ctx = await build_context()
            autonomy = get_autonomy_level()
            open_prs = await get_open_prs()

            ctx_hash = _compute_context_hash(ctx, open_prs)
            if ctx_hash == get_context_hash():
                if config.VERBOSE_TICKS:
                    console.print("[dim]no changes detected · skipping LLM[/dim]")
                return
            set_context_hash(ctx_hash)

            pr_summary = ""
            if open_prs:
                pr_lines = []
                for p in open_prs:
                    line = f"  PR #{p['number']}: {p['title']} ({p['days_open']}d open, review: {p['review_status']}, stale: {p['is_stale']})"
                    if p.get("diff"):
                        line += f"\n  diff:\n{p['diff'][:600]}"
                    pr_lines.append(line)
                pr_summary = "\nOpen PRs:\n" + "\n".join(pr_lines)

            prompt = (
                f"Repo state: {ctx}{pr_summary}\n"
                f"Autonomy: {autonomy}\n"
                f"Respond with one of:\n"
                f"  SLEEP\n"
                f"  ACTION: <instruction>\n"
                f"  COMMENT: <pr_number>: <message>\n"
                f"Use COMMENT only if there is an open PR and something specific worth noting on it."
            )

            response = await ask_tick_model(prompt)

            if not response or response.startswith("SLEEP"):
                if config.VERBOSE_TICKS:
                    fs = ctx.get('filesystem', {})
                    modified = fs.get('modified_files_last_24h', {})
                    total_modified = sum(len(v) for v in modified.values())
                    console.print(f"[dim]autonomy: {autonomy} · todos: {len(fs.get('todos', []))} · modified: {total_modified} · never_imported: {ctx.get('never_imported', [])} · dangling: {ctx.get('dangling_imports', [])} · SLEEP[/dim]")
                return

            if response.startswith("ACTION:"):
                instruction = response[len("ACTION:"):].strip()
                if already_notified_today(instruction):
                    return
                log_action(instruction)
                write_to_daily_log(instruction)
                if config.VERBOSE_TICKS:
                    fs = ctx.get('filesystem', {})
                    modified = fs.get('modified_files_last_24h', {})
                    total_modified = sum(len(v) for v in modified.values())
                    console.print(f"[dim]autonomy: {autonomy} · todos: {len(fs.get('todos', []))} · modified: {total_modified} · {response}[/dim]")
                if autonomy == "high":
                    notify(instruction)
                else:
                    print_brief(instruction)

            elif response.startswith("COMMENT:"):
                body = response[len("COMMENT:"):].strip()
                parts = body.split(":", 1)
                if len(parts) == 2:
                    try:
                        pr_number = int(parts[0].strip())
                        message = parts[1].strip()
                        dedup_key = f"comment:pr#{pr_number}"
                        if already_notified_today(dedup_key):
                            return
                        if config.VERBOSE_TICKS:
                            fs = ctx.get('filesystem', {})
                            modified = fs.get('modified_files_last_24h', {})
                            total_modified = sum(len(v) for v in modified.values())
                            console.print(f"[dim]autonomy: {autonomy} · todos: {len(fs.get('todos', []))} · modified: {total_modified} · {response}[/dim]")
                        if autonomy == "low":
                            log_action(dedup_key, pr_id=pr_number)
                            print_brief("wants to post a PR comment, step away or approve manually")
                            return
                        ok = post_pr_comment(pr_number, message)
                        if ok:
                            log_action(dedup_key, pr_id=pr_number)
                            write_to_daily_log(f"commented on PR #{pr_number}: {message}")
                            print_brief(f"commented on PR #{pr_number}")
                    except ValueError:
                        pass

    except asyncio.TimeoutError:
        console.print("[yellow][auto-agent] tick timed out[/yellow]")
        return
    except Exception as e:
        import traceback
        console.print(f"[red][auto-agent] tick error:[/red] {e}")
        console.print(f"[red]{traceback.format_exc()}[/red]")
