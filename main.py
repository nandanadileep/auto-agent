import asyncio
import sys

from rich.console import Console

console = Console()
scheduler = None

if __name__ == "__main__":
    try:
        from daemon.scheduler import start_scheduler

        console.print("[dim]KAIROS starting...[/dim]")
        scheduler = start_scheduler()
        console.print("[dim]KAIROS running. Press Ctrl+C to stop.[/dim]")
        asyncio.get_event_loop().run_forever()

    except KeyboardInterrupt:
        if scheduler:
            scheduler.shutdown()
        console.print("[dim]KAIROS stopped.[/dim]")

    except Exception as e:
        console.print(f"[red]KAIROS error:[/red] {e}")
        if scheduler:
            scheduler.shutdown()
        sys.exit(1)
