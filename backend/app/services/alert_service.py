"""
Alert creation service.
Handles alert creation, zone health score updates,
WebSocket broadcasts, and webhook delivery.
"""
import logging
from datetime import datetime
from typing import Optional, Dict
from bson import ObjectId

from app.core.database import get_db
from app.models.alert import AlertCreate
from app.services.email_service import send_deforestation_alert_email

logger = logging.getLogger(__name__)


def _determine_severity(ndvi_delta: float) -> str:
    """Determine alert severity based on NDVI drop magnitude."""
    if ndvi_delta <= -0.35:
        return "critical"
    elif ndvi_delta <= -0.25:
        return "high"
    elif ndvi_delta <= -0.15:
        return "medium"
    else:
        return "low"


def _update_health_score(current_health: int, ndvi_delta: float) -> int:
    """Update zone health score based on NDVI delta."""
    new_score = current_health + int(ndvi_delta * 100)
    return max(0, min(100, new_score))


def _health_to_status(health_score: int) -> str:
    """Convert health score to status string."""
    if health_score > 70:
        return "healthy"
    elif health_score >= 40:
        return "warning"
    else:
        return "critical"


async def create_alert_if_triggered(
    zone: Dict,
    change_result: Dict,
    websocket_broadcast_fn,
) -> Optional[Dict]:
    """
    Evaluate change detection results and create an alert if thresholds are exceeded.
    Updates zone health score and broadcasts via WebSocket.

    Args:
        zone: Zone document from MongoDB
        change_result: Output from change_detection.detect_change()
        websocket_broadcast_fn: Async callable to broadcast WS messages

    Returns:
        Created alert document or None
    """
    ndvi_delta = change_result.get("ndvi_delta", 0.0)
    confidence = change_result.get("confidence", 0.0)
    ndvi_drop_threshold = zone.get("ndvi_drop_threshold", 0.15)
    confidence_threshold = zone.get("confidence_threshold", 0.70)
    zone_id = str(zone["_id"])

    # Check if alert conditions are met
    if not (confidence >= confidence_threshold and ndvi_delta <= -ndvi_drop_threshold):
        logger.info(
            f"Zone {zone['name']}: No alert triggered. "
            f"confidence={confidence:.2f} (need {confidence_threshold}), "
            f"ndvi_delta={ndvi_delta:.3f} (need -{ndvi_drop_threshold})"
        )
        return None

    db = get_db()
    severity = _determine_severity(ndvi_delta)
    detected_at = datetime.utcnow()

    alert_doc = {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "detected_at": detected_at,
        "ndvi_before": change_result["ndvi_before"],
        "ndvi_after": change_result["ndvi_after"],
        "ndvi_delta": ndvi_delta,
        "evi_before": change_result["evi_before"],
        "evi_after": change_result["evi_after"],
        "change_area_ha": change_result["affected_area_ha"],
        "confidence": confidence,
        "severity": severity,
        "change_map_url": change_result["change_map_url"],
        "status": "new",
        "notified": False,
        "notified_at": None,
        "notes": "",
    }

    # Insert alert into MongoDB
    result = await db["alerts"].insert_one(alert_doc)
    alert_doc["_id"] = str(result.inserted_id)

    logger.info(
        f"Alert created for zone {zone['name']}: "
        f"severity={severity}, confidence={confidence:.0%}, "
        f"area={change_result['affected_area_ha']:.1f}ha"
    )

    # Update zone health score and status
    current_health = zone.get("health_score", 100)
    new_health = _update_health_score(current_health, ndvi_delta)
    new_status = _health_to_status(new_health)

    await db["zones"].update_one(
        {"_id": zone["_id"]},
        {
            "$set": {
                "health_score": new_health,
                "status": new_status,
                "last_scanned_at": detected_at,
            }
        },
    )

    # Broadcast health update via WebSocket
    try:
        await websocket_broadcast_fn({
            "type": "health_update",
            "zone_id": zone_id,
            "health_score": new_health,
            "status": new_status,
        })
    except Exception as e:
        logger.warning(f"WS health broadcast failed: {e}")

    # Broadcast alert via WebSocket
    try:
        await websocket_broadcast_fn({
            "type": "alert",
            "alert_id": alert_doc["_id"],
            "zone_name": zone["name"],
            "severity": severity,
            "confidence": confidence,
            "change_area_ha": change_result["affected_area_ha"],
            "detected_at": detected_at.isoformat(),
        })
    except Exception as e:
        logger.warning(f"WS alert broadcast failed: {e}")

    # Send email notifications
    alert_emails = zone.get("alert_emails", [])
    if alert_emails:
        try:
            await send_deforestation_alert_email(
                recipients=alert_emails,
                alert=alert_doc,
                zone=zone,
            )
            await db["alerts"].update_one(
                {"_id": result.inserted_id},
                {"$set": {"notified": True, "notified_at": datetime.utcnow()}},
            )
        except Exception as e:
            logger.error(f"Email notification failed for zone {zone['name']}: {e}")

    # Send webhook notification if configured
    webhook_url = zone.get("webhook_url")
    if webhook_url:
        await _send_webhook(webhook_url, alert_doc)

    return alert_doc


async def _send_webhook(webhook_url: str, alert: Dict) -> None:
    """POST alert payload to the configured webhook URL."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                webhook_url,
                json={
                    "event": "deforestation_alert",
                    "alert_id": str(alert.get("_id", "")),
                    "zone_name": alert["zone_name"],
                    "severity": alert["severity"],
                    "confidence": alert["confidence"],
                    "ndvi_delta": alert["ndvi_delta"],
                    "change_area_ha": alert["change_area_ha"],
                    "detected_at": alert["detected_at"].isoformat()
                    if isinstance(alert["detected_at"], datetime)
                    else alert["detected_at"],
                    "change_map_url": alert["change_map_url"],
                },
                headers={"Content-Type": "application/json"},
            )
            logger.info(f"Webhook delivered to {webhook_url}: HTTP {resp.status_code}")
    except Exception as e:
        logger.error(f"Webhook delivery failed to {webhook_url}: {e}")
