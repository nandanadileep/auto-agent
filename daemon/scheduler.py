from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TICK_INTERVAL_MINUTES
from daemon.tick import tick
from memory.dream import run_autodream


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(tick, "interval", minutes=TICK_INTERVAL_MINUTES)
    scheduler.add_job(run_autodream, "cron", hour=0, minute=0)
    scheduler.start()
    return scheduler
