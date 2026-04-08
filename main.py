import asyncio
import sys

from rich.console import Console

console = Console()


async def run():
    from daemon.scheduler import start_scheduler
    from watchers.filesystem import watch_and_tick

    scheduler = start_scheduler()
    console.print("[dim]auto-agent running. Press Ctrl+C to stop.[/dim]")
    try:
        await asyncio.gather(
            watch_and_tick(),
            _keepalive(),
        )
    finally:
        scheduler.shutdown()


async def _keepalive():
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        console.print("[dim]auto-agent starting...[/dim]")
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("[dim]auto-agent stopped.[/dim]")
    except Exception as e:
        console.print(f"[red]auto-agent error:[/red] {e}")
        sys.exit(1)
