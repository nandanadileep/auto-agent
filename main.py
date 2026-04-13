import asyncio
import sys
try:
    from utils import deleted_module  # demo: dangling import
except ImportError:
    pass
try:
    from utils import deleted_module  # demo: dangling import
except ImportError:
    pass
try:
    from utils import deleted_module  # demo: dangling import
except ImportError:
    pass
import threading
import time

import uvicorn
from rich.console import Console

import config

console = Console()


def _start_dashboard():
    from dashboard.server import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")


def _setup_ngrok():
    import os
    time.sleep(2)  # wait for uvicorn to be ready
    try:
        from pyngrok import conf, ngrok
        from github import Github

        auth_token = os.getenv("NGROK_AUTHTOKEN", "")
        if not auth_token:
            console.print("[dim]webhook tunnel skipped — set NGROK_AUTHTOKEN in .env to enable[/dim]")
            return

        conf.get_default().log_event_callback = None
        conf.get_default().auth_token = auth_token

        tunnel = ngrok.connect(8000, "http")
        public_url = tunnel.public_url.replace("http://", "https://")
        webhook_url = f"{public_url}/webhook/github"

        console.print(f"[dim]ngrok tunnel: {public_url}[/dim]")

        gh = Github(config.GITHUB_TOKEN)
        repo = gh.get_repo(config.GITHUB_REPO)

        hook_config = {
            "url": webhook_url,
            "content_type": "json",
            "secret": config.GITHUB_WEBHOOK_SECRET,
        }
        events = ["pull_request", "pull_request_review", "push"]

        existing = None
        for hook in repo.get_hooks():
            if "webhook/github" in hook.config.get("url", ""):
                existing = hook
                break

        if existing:
            existing.edit("web", hook_config, events=events, active=True)
        else:
            repo.create_hook("web", hook_config, events=events, active=True)

        console.print(f"[dim]webhook registered → {webhook_url}[/dim]")

    except ImportError:
        console.print("[dim]pyngrok not installed — skipping webhook setup (pip install pyngrok)[/dim]")
    except Exception as e:
        console.print(f"[yellow]webhook setup failed: {e}[/yellow]")


async def run():
    from daemon.scheduler import start_scheduler
    from watchers.filesystem import watch_and_tick

    dashboard_thread = threading.Thread(target=_start_dashboard, daemon=True)
    dashboard_thread.start()
    console.print("[dim]auto dream dashboard → http://localhost:8000[/dim]")

    ngrok_thread = threading.Thread(target=_setup_ngrok, daemon=True)
    ngrok_thread.start()

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
