import asyncio
import sys

from rich.console import Console

console = Console()


async def run():
    from daemon.scheduler import start_scheduler

    scheduler = start_scheduler()
    console.print("[dim]auto-agent running. Press Ctrl+C to stop.[/dim]")
    try:
        while True:
            await asyncio.sleep(60)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    try:
        console.print("[dim]auto-agent starting...[/dim]")
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("[dim]auto-agent stopped.[/dim]")
    except Exception as e:
        console.print(f"[red]auto-agent error:[/red] {e}")
        sys.exit(1)
