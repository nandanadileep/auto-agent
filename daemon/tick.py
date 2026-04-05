import asyncio

from rich.console import Console

import config
from actions import notify, print_brief
from agent.llm import ask_tick_model
from context import build_context
from presence import get_autonomy_level
from state import already_notified_today, log_action

console = Console()


async def tick():
    try:
        async with asyncio.timeout(config.TICK_TIMEOUT_SECONDS):
            ctx = await build_context()
            autonomy = get_autonomy_level()

            prompt = f"Repo state: {ctx}\nAutonomy: {autonomy}\nRespond SLEEP or ACTION: <instruction>."

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

    except asyncio.TimeoutError:
        console.print("[yellow][kairos] tick timed out[/yellow]")
        return
    except Exception as e:
        import traceback
        console.print(f"[red][kairos] tick error:[/red] {e}")
        console.print(f"[red]{traceback.format_exc()}[/red]")
