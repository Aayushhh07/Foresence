"""
Alerts API routes.
"""
import logging
from typing import Optional
from bson import ObjectId
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pymongo import ReturnDocument

from app.core.database import get_db
from app.models.alert import AlertStatusUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _serialize_alert(doc: dict) -> dict:
    """Convert MongoDB alert document to JSON-serializable format."""
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("detected_at"), datetime):
        doc["detected_at"] = doc["detected_at"].isoformat()
    if isinstance(doc.get("notified_at"), datetime):
        doc["notified_at"] = doc["notified_at"].isoformat()
    return doc


@router.get("", response_model=dict)
async def list_alerts(
    zone_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """List alerts with optional filters."""
    db = get_db()
    query = {}

    if zone_id:
        query["zone_id"] = zone_id
    if severity and severity in ("low", "medium", "high", "critical"):
        query["severity"] = severity
    if status and status in ("new", "acknowledged", "resolved"):
        query["status"] = status

    cursor = db["alerts"].find(query).sort("detected_at", -1).skip(skip).limit(limit)
    alerts = []
    async for doc in cursor:
        alerts.append(_serialize_alert(doc))

    total = await db["alerts"].count_documents(query)
    return {
        "success": True,
        "data": {"alerts": alerts, "total": total, "limit": limit, "skip": skip},
        "message": f"{len(alerts)} alerts returned",
    }


@router.get("/summary", response_model=dict)
async def alerts_summary():
    """
    Count alerts by workflow status plus total (for inbox UI tabs).
    Declared before /{alert_id} so ``summary`` is not parsed as an ObjectId.
    """
    db = get_db()
    counts = {"new": 0, "acknowledged": 0, "resolved": 0, "total": 0}
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    cursor = db["alerts"].aggregate(pipeline)
    async for row in cursor:
        status_key = row.get("_id") or ""
        cnt = int(row.get("count", 0))
        counts["total"] += cnt
        if status_key in counts:
            counts[status_key] = cnt
    return {
        "success": True,
        "data": counts,
        "message": "Alert counts by status",
    }


@router.get("/{alert_id}", response_model=dict)
async def get_alert(alert_id: str):
    """Get a single alert by ID."""
    db = get_db()
    try:
        oid = ObjectId(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid alert ID")

    doc = await db["alerts"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"success": True, "data": _serialize_alert(doc), "message": "Alert retrieved"}


@router.put("/{alert_id}/status", response_model=dict)
async def update_alert_status(alert_id: str, update: AlertStatusUpdate):
    """Update an alert's status (acknowledged / resolved)."""
    db = get_db()
    try:
        oid = ObjectId(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid alert ID")

    updates = {"status": update.status}
    if update.notes is not None:
        updates["notes"] = update.notes

    result = await db["alerts"].find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "success": True,
        "data": _serialize_alert(result),
        "message": f"Alert marked as {update.status}",
    }
