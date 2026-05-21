"""
Health check endpoint.
"""
import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.zone import GeoJSONPolygon
from app.services.sentinel_service import check_satellite_availability

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


class SatelliteCheckRequest(BaseModel):
    geojson: GeoJSONPolygon
    lookback_days: int = Field(default=30, ge=1, le=180)
    require_copernicus_auth: bool = False


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
        if redis is None:
            redis_status = "memory-only (no Redis URL configured)"
        else:
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


@router.post("/satellite-check", response_model=dict)
async def satellite_check(payload: SatelliteCheckRequest):
    """
    Validate satellite API reachability and recent scene availability for a polygon.
    """
    check = await check_satellite_availability(
        geojson_coords=payload.geojson.coordinates,
        lookback_days=payload.lookback_days,
        require_copernicus_auth=payload.require_copernicus_auth,
    )

    stac_scene = check.get("stac", {}).get("latest_scene")
    cop_scene = check.get("copernicus", {}).get("latest_scene")
    has_scene = bool(stac_scene or cop_scene)

    return {
        "success": True,
        "data": {
            **check,
            "has_recent_scene": has_scene,
        },
        "message": "Satellite connectivity check complete",
    }
