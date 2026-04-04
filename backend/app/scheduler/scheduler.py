"""
APScheduler setup and lifecycle management.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler AsyncIOScheduler."""
    global _scheduler
    _scheduler = AsyncIOScheduler(
        jobstores={"default": MemoryJobStore()},
        executors={"default": AsyncIOExecutor()},
        job_defaults={
            "coalesce": True,       # Collapse missed runs into one
            "max_instances": 1,     # Only one instance of each job at a time
            "misfire_grace_time": 300,  # 5 minutes grace window
        },
        timezone="UTC",
    )
    logger.info("APScheduler created.")
    return _scheduler


def get_scheduler() -> AsyncIOScheduler:
    """Return the active scheduler instance."""
    return _scheduler


def start_scheduler(scan_interval_hours: int = 12) -> None:
    """Start the scheduler and register the zone scan job."""
    global _scheduler
    if _scheduler is None:
        create_scheduler()

    from app.scheduler.jobs import run_all_zone_scans

    # Register recurring scan job
    _scheduler.add_job(
        run_all_zone_scans,
        trigger="interval",
        hours=scan_interval_hours,
        id="zone_scan_job",
        replace_existing=True,
        name="Satellite Zone Scan",
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started. Zone scans every {scan_interval_hours} hours."
    )


def stop_scheduler() -> None:
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
