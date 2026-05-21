"""
Zones API routes — CRUD + manual scan trigger.
"""
import logging
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pyproj import Geod

from app.core.database import get_db
from app.models.zone import ZoneCreate, ZoneUpdate, ZoneResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/zones", tags=["zones"])


def _compute_area_ha(geojson_coords: list) -> float:
    """Compute polygon area in hectares using geodesic computation."""
    try:
        geod = Geod(ellps="WGS84")
        ring = geojson_coords[0]
        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]
        area_m2, _ = geod.polygon_area_perimeter(lons, lats)
        return abs(area_m2) / 10000.0
    except Exception:
        return 0.0


def _serialize_zone(doc: dict) -> dict:
    """Convert MongoDB zone document to API response format."""
    doc["_id"] = str(doc["_id"])
    return doc


@router.post("", response_model=dict)
async def create_zone(zone_data: ZoneCreate, background_tasks: BackgroundTasks):
    """Create a new forest zone with the given GeoJSON polygon."""
    db = get_db()

    area_ha = _compute_area_ha(zone_data.geojson.coordinates)

    zone_doc = {
        "name": zone_data.name,
        "description": zone_data.description,
        "geojson": zone_data.geojson.model_dump(),
        "area_ha": area_ha,
        "ndvi_drop_threshold": zone_data.ndvi_drop_threshold,
        "confidence_threshold": zone_data.confidence_threshold,
        "alert_emails": zone_data.alert_emails,
        "webhook_url": zone_data.webhook_url,
        "health_score": 100,
        "status": "healthy",
        "active": True,
        "created_at": datetime.utcnow(),
        "last_scanned_at": None,
    }

    result = await db["zones"].insert_one(zone_doc)
    zone_doc["_id"] = str(result.inserted_id)

    logger.info(f"Zone created: {zone_data.name} ({area_ha:.1f} ha)")

    # Queue background task to seed historical scans (Pass 1 baseline, Pass 2 current)
    from app.scheduler.jobs import seed_historical_zone_data
    background_tasks.add_task(seed_historical_zone_data, zone_doc["_id"])

    return {"success": True, "data": zone_doc, "message": "Zone created successfully"}



@router.get("", response_model=dict)
async def list_zones():
    """List all forest zones."""
    db = get_db()
    zones = []
    async for doc in db["zones"].find().sort("created_at", -1):
        zones.append(_serialize_zone(doc))
    return {"success": True, "data": zones, "message": f"{len(zones)} zones found"}


@router.get("/{zone_id}", response_model=dict)
async def get_zone(zone_id: str):
    """Get a single zone by ID."""
    db = get_db()
    try:
        oid = ObjectId(zone_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid zone ID format")

    doc = await db["zones"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Zone not found")

    return {"success": True, "data": _serialize_zone(doc), "message": "Zone retrieved"}


@router.put("/{zone_id}", response_model=dict)
async def update_zone(zone_id: str, update_data: ZoneUpdate):
    """Update zone settings."""
    db = get_db()
    try:
        oid = ObjectId(zone_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid zone ID format")

    updates = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db["zones"].find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Zone not found")

    return {"success": True, "data": _serialize_zone(result), "message": "Zone updated"}


@router.delete("/{zone_id}", response_model=dict)
async def delete_zone(zone_id: str):
    """Delete a zone and its associated data."""
    db = get_db()
    try:
        oid = ObjectId(zone_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid zone ID format")

    zone = await db["zones"].find_one({"_id": oid})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    await db["zones"].delete_one({"_id": oid})

    # Also soft-clean related data
    deleted_alerts = await db["alerts"].delete_many({"zone_id": zone_id})
    logger.info(
        f"Zone {zone['name']} deleted. "
        f"Removed {deleted_alerts.deleted_count} related alerts."
    )

    return {"success": True, "data": None, "message": "Zone deleted successfully"}


@router.post("/{zone_id}/scan", response_model=dict)
async def trigger_manual_scan(zone_id: str, background_tasks: BackgroundTasks):
    """Trigger a manual satellite scan for a single zone."""
    db = get_db()
    try:
        oid = ObjectId(zone_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid zone ID format")

    zone = await db["zones"].find_one({"_id": oid})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    if not zone.get("active", True):
        raise HTTPException(status_code=400, detail="Zone is inactive")

    # Import here to avoid circular imports at module load time
    from app.scheduler.jobs import scan_single_zone

    background_tasks.add_task(scan_single_zone, str(zone["_id"]))

    logger.info(f"Manual scan triggered for zone: {zone['name']}")
    return {
        "success": True,
        "data": {"zone_id": zone_id, "zone_name": zone["name"]},
        "message": "Scan triggered. Results will appear shortly.",
    }
