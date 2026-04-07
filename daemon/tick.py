import asyncio

from rich.console import Console

import config
from actions import notify, post_pr_comment, print_brief
from agent.llm import ask_tick_model
from context import build_context
from presence import get_autonomy_level
from state import already_notified_today, log_action
from watchers.github import get_open_prs

console = Console()


async def tick():
    try:
        async with asyncio.timeout(config.TICK_TIMEOUT_SECONDS):
            ctx = await build_context()
            autonomy = get_autonomy_level()
            open_prs = await get_open_prs()

            pr_summary = ""
            if open_prs:
                pr_lines = [f"  PR #{p['number']}: {p['title']} ({p['days_open']}d open, review: {p['review_status']}, stale: {p['is_stale']})" for p in open_prs]
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
                return

            if response.startswith("ACTION:"):
                instruction = response[len("ACTION:"):].strip()
                log_action(instruction)
                if already_notified_today(instruction):
                    return
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
                        if not already_notified_today(f"comment:pr#{pr_number}:{message}"):
                            post_pr_comment(pr_number, message)
                            log_action(f"comment:pr#{pr_number}:{message}", pr_id=pr_number)
                            print_brief(f"commented on PR #{pr_number}")
                    except ValueError:
                        pass

    except asyncio.TimeoutError:
        console.print("[yellow][kairos] tick timed out[/yellow]")
        return
    except Exception as e:
        import traceback
        console.print(f"[red][kairos] tick error:[/red] {e}")
        console.print(f"[red]{traceback.format_exc()}[/red]")
