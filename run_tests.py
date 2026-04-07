import asyncio
from rich.console import Console

console = Console()


def section(title):
    console.print(f"\n[bold cyan]── {title} ──[/bold cyan]")


def ok(msg):
    console.print(f"  [green]✓[/green] {msg}")


def fail(msg, e):
    console.print(f"  [red]✗[/red] {msg}: {e}")


# ── presence ──────────────────────────────────────────────
def test_presence():
    section("presence")
    try:
        from presence import get_autonomy_level
        level = get_autonomy_level()
        assert level in ("low", "medium", "high")
        ok(f"autonomy level: {level}")
    except Exception as e:
        fail("get_autonomy_level", e)


# ── state ─────────────────────────────────────────────────
def test_state():
    section("state")
    try:
        from state import log_action, already_notified_today, get_todays_actions
        log_action("test action from run_tests", pr_id=None)
        ok("log_action wrote to db")

        result = already_notified_today("test action from run_tests")
        assert result is True
        ok("already_notified_today returns True for logged action")

        actions = get_todays_actions()
        assert any(a["action"] == "test action from run_tests" for a in actions)
        ok(f"get_todays_actions returned {len(actions)} action(s)")
    except Exception as e:
        fail("state", e)


# ── memory/daily_log ──────────────────────────────────────
def test_daily_log():
    section("memory/daily_log")
    try:
        from memory.daily_log import write_to_daily_log, get_todays_log
        write_to_daily_log("test observation from run_tests")
        ok("write_to_daily_log wrote entry")

        log = get_todays_log()
        assert "test observation from run_tests" in log
        ok("get_todays_log returned today's log")
    except Exception as e:
        fail("daily_log", e)


# ── memory/memory_md ──────────────────────────────────────
def test_memory_md():
    section("memory/memory_md")
    try:
        from memory.memory_md import write_memory_md, read_memory_md
        write_memory_md("# test memory\n- line one\n- line two")
        ok("write_memory_md wrote file")

        content = read_memory_md()
        assert "test memory" in content
        ok("read_memory_md returned content")
    except Exception as e:
        fail("memory_md", e)


# ── actions ───────────────────────────────────────────────
def test_actions():
    section("actions")
    try:
        from actions import print_brief
        print_brief("test nudge from run_tests")
        ok("print_brief printed line")
    except Exception as e:
        fail("print_brief", e)

    try:
        from actions import notify
        notify("test desktop notification from KAIROS")
        ok("notify fired (check your desktop)")
    except Exception as e:
        fail("notify", e)


# ── context ───────────────────────────────────────────────
async def test_context():
    section("context")
    try:
        from context import build_context
        ctx = await build_context()
        assert isinstance(ctx, dict)
        assert "git" in ctx and "filesystem" in ctx
        ok(f"build_context returned keys: {list(ctx.keys())}")
        ok(f"git commits found: {len(ctx['git'].get('history', []))}")
        ok(f"todos found: {len(ctx['filesystem'].get('todos', []))}")
    except Exception as e:
        fail("build_context", e)


# ── watchers/github ───────────────────────────────────────
async def test_github():
    section("watchers/github")
    try:
        from watchers.github import get_open_prs, get_recent_commits
        prs = await get_open_prs()
        ok(f"get_open_prs returned {len(prs)} open PR(s)")

        commits = await get_recent_commits(5)
        ok(f"get_recent_commits returned {len(commits)} commit(s)")
        if commits:
            ok(f"latest commit: {commits[0]['sha']} — {commits[0]['message'][:50]}")
    except Exception as e:
        fail("github watcher", e)


# ── agent/llm ─────────────────────────────────────────────
async def test_llm():
    section("agent/llm")
    try:
        from agent.llm import ask_tick_model
        response = await ask_tick_model("Repo has a TODO: add password hashing. Autonomy: low.")
        ok(f"ask_tick_model responded: {response}")
    except Exception as e:
        fail("ask_tick_model", e)

    try:
        from agent.llm import ask_dream_model
        response = await ask_dream_model("Summarize in one sentence: today I fixed a bug in auth.")
        ok(f"ask_dream_model responded: {response[:80]}")
    except Exception as e:
        fail("ask_dream_model", e)


# ── tick ──────────────────────────────────────────────────
async def test_tick():
    section("daemon/tick")
    try:
        from daemon.tick import tick
        await tick()
        ok("tick() completed without error")
    except Exception as e:
        fail("tick", e)


# ── main ──────────────────────────────────────────────────
async def main():
    console.print("[bold]KAIROS feature test[/bold]")

    test_presence()
    test_state()
    test_daily_log()
    test_memory_md()
    test_actions()
    await test_context()
    await test_github()
    await test_llm()
    await test_tick()

    console.print("\n[bold]done.[/bold]")


if __name__ == "__main__":
    asyncio.run(main())
