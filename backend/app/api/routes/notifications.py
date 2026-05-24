"""
Email notification routes — manual zone health reports.
"""
import logging
from datetime import datetime
from typing import List, Dict

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.notification import ZoneReportRequest
from app.services.email_service import (
    send_zone_health_report_email,
    is_email_configured,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _format_ts(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M UTC")
    if value:
        return str(value)[:19]
    return "Never"


@router.post("/zone-report", response_model=dict)
async def send_zone_health_report(payload: ZoneReportRequest):
    """
    Email a health summary for selected zones (health, NDVI, alerts, latest scan image).
    Recipients: request body, else GLOBAL_ALERT_EMAILS from env.
    """
    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Email not configured. Set RESEND_API_KEY + ALERT_FROM_EMAIL, "
                "or SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD (see backend/.env.example)."
            ),
        )

    recipients = list(payload.recipients or []) or list(settings.global_alert_emails_list)
    if not recipients:
        raise HTTPException(
            status_code=400,
            detail="No recipients. Add emails in the request body or set GLOBAL_ALERT_EMAILS in .env",
        )

    db = get_db()
    zones_report: List[Dict] = []

    for zone_id in payload.zone_ids:
        try:
            oid = ObjectId(zone_id)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid zone id: {zone_id}")

        zone = await db["zones"].find_one({"_id": oid})
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone not found: {zone_id}")

        zid = str(zone["_id"])
        latest_snap = await db["ndvi_snapshots"].find_one(
            {"zone_id": zid},
            sort=[("timestamp", -1)],
        )
        new_alerts = await db["alerts"].count_documents(
            {"zone_id": zid, "status": "new"}
        )

        zones_report.append(
            {
                "name": zone.get("name"),
                "status": zone.get("status", "healthy"),
                "health_score": zone.get("health_score", 100),
                "area_ha": zone.get("area_ha", 0),
                "latest_ndvi": (
                    f"{latest_snap['ndvi_mean']:.3f}"
                    if latest_snap and latest_snap.get("ndvi_mean") is not None
                    else "—"
                ),
                "latest_image_url": latest_snap.get("image_url") if latest_snap else None,
                "new_alerts": new_alerts,
                "last_scanned": _format_ts(zone.get("last_scanned_at")),
            }
        )

    try:
        await send_zone_health_report_email(recipients, zones_report)
    except Exception as e:
        logger.error(f"Zone report email failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to send email: {e}")

    return {
        "success": True,
        "data": {
            "zones_count": len(zones_report),
            "recipients": recipients,
            "provider": settings.effective_email_provider,
        },
        "message": f"Health report emailed to {len(recipients)} recipient(s) for {len(zones_report)} zone(s)",
    }


@router.get("/email-status", response_model=dict)
async def email_status():
    """Check whether email is configured and which provider is active."""
    configured = is_email_configured()
    return {
        "success": True,
        "data": {
            "configured": configured,
            "provider": settings.effective_email_provider if configured else None,
            "auto_email_on_alert": settings.auto_email_on_alert,
            "global_recipients": settings.global_alert_emails_list,
            "from_email": settings.alert_from_email if configured else None,
        },
        "message": "Email configuration status",
    }
