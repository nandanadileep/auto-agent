import asyncio
import sys

from rich.console import Console

console = Console()


async def run():
    from daemon.scheduler import start_scheduler

    scheduler = start_scheduler()
    console.print("[dim]KAIROS running. Press Ctrl+C to stop.[/dim]")
    try:
        while True:
            await asyncio.sleep(60)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    try:
        console.print("[dim]KAIROS starting...[/dim]")
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("[dim]KAIROS stopped.[/dim]")
    except Exception as e:
        console.print(f"[red]KAIROS error:[/red] {e}")
        sys.exit(1)
