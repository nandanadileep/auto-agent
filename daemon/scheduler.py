from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor

from config import TICK_INTERVAL_MINUTES
from daemon.tick import tick
from memory.dream import run_autodream


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(executors={"default": AsyncIOExecutor()})
    scheduler.add_job(tick, "interval", minutes=TICK_INTERVAL_MINUTES, misfire_grace_time=30)
    scheduler.add_job(run_autodream, "cron", hour=0, minute=0)
    scheduler.start()
    return scheduler
