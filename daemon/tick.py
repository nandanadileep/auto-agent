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

            prompt = f"""You are KAIROS, a silent background coding agent.

Current repo state:
{ctx}

Autonomy level: {autonomy}
- high: user is away, act freely
- medium: user stepped away briefly, notify but no public actions
- low: user is present, surface findings quietly in terminal only

Rules:
- If there is something specific and useful to tell the developer, respond with: ACTION: <what to do>
- If there is nothing useful to say, respond with: SLEEP
- Never narrate. Never say you checked something. Never explain your reasoning.
- SLEEP is always right when in doubt."""

            response = await ask_tick_model(prompt)

            if response.startswith("SLEEP"):
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
        return
    except Exception as e:
        console.print(f"[red][kairos] tick error:[/red] {e}")
