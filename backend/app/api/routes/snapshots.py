"""
Snapshots API routes — NDVI timeseries data.
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


def _serialize_snapshot(doc: dict) -> dict:
    """Serialize a snapshot document."""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].isoformat()
    return doc


@router.get("", response_model=dict)
async def list_snapshots(
    zone_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="ISO datetime filter"),
    end_date: Optional[str] = Query(None, description="ISO datetime filter"),
    limit: int = Query(90, ge=1, le=500),
):
    """List NDVI snapshots with optional zone and date filters."""
    db = get_db()
    query = {}

    if zone_id:
        query["zone_id"] = zone_id

    if start_date or end_date:
        ts_filter = {}
        if start_date:
            try:
                ts_filter["$gte"] = datetime.fromisoformat(start_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                ts_filter["$lte"] = datetime.fromisoformat(end_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        query["timestamp"] = ts_filter

    snapshots = []
    async for doc in (
        db["ndvi_snapshots"].find(query).sort("timestamp", -1).limit(limit)
    ):
        snapshots.append(_serialize_snapshot(doc))

    return {
        "success": True,
        "data": snapshots,
        "message": f"{len(snapshots)} snapshots returned",
    }


@router.get("/latest/{zone_id}", response_model=dict)
async def get_latest_snapshot(zone_id: str):
    """Get the latest NDVI snapshot for a specific zone."""
    db = get_db()
    doc = await db["ndvi_snapshots"].find_one(
        {"zone_id": zone_id},
        sort=[("timestamp", -1)],
    )
    if not doc:
        return {
            "success": True,
            "data": None,
            "message": "No snapshot found for this zone",
        }

    return {
        "success": True,
        "data": _serialize_snapshot(doc),
        "message": "Latest snapshot retrieved",
    }
