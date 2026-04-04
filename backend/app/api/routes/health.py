"""
Health check endpoint.
"""
import logging
from datetime import datetime

from fastapi import APIRouter

from app.core.database import get_db
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=dict)
async def health_check():
    """
    System health check.
    Returns status of DB, Redis, and scheduler.
    """
    # Check DB
    db_status = "connected"
    try:
        db = get_db()
        await db.command("ping")
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"

    # Check Redis
    redis_status = "connected"
    try:
        redis = get_redis()
        await redis.ping()
    except Exception as e:
        redis_status = f"error: {str(e)[:50]}"

    # Check scheduler
    scheduler_status = "unknown"
    try:
        from app.scheduler.scheduler import get_scheduler
        sched = get_scheduler()
        scheduler_status = "running" if sched and sched.running else "stopped"
    except Exception:
        scheduler_status = "not initialized"

    # Get last scan time from DB
    last_scan_at = None
    try:
        db = get_db()
        latest = await db["zones"].find_one(
            {"last_scanned_at": {"$ne": None}},
            sort=[("last_scanned_at", -1)],
        )
        if latest and latest.get("last_scanned_at"):
            last_scan_at = latest["last_scanned_at"].isoformat()
    except Exception:
        pass

    overall = (
        "healthy"
        if db_status == "connected" and redis_status == "connected"
        else "degraded"
    )

    return {
        "success": True,
        "data": {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": db_status,
                "redis": redis_status,
                "scheduler": scheduler_status,
            },
            "last_scan_at": last_scan_at,
        },
        "message": f"System is {overall}",
    }
