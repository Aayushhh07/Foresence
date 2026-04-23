"""
Demo seed endpoint.
Populates MongoDB with realistic forest zones, NDVI snapshots, and alerts
so the full dashboard is demo-ready without any external API calls.
"""
import logging
import random
from datetime import datetime, timedelta

from fastapi import APIRouter

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/demo", tags=["demo"])

# ── Seed data ──────────────────────────────────────────────────────────────

ZONES = [
    {
        "name": "Western Ghats Reserve",
        "description": "Biodiversity hotspot along India's western coast — dense evergreen forest.",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [76.5, 11.8], [76.9, 11.8], [76.9, 12.2],
                [76.5, 12.2], [76.5, 11.8],
            ]],
        },
        "area_ha": 42500.0,
        "health_score": 61,
        "status": "warning",
    },
    {
        "name": "Sundarbans Mangrove Belt",
        "description": "World's largest mangrove forest — critical tiger habitat in West Bengal.",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [88.8, 21.8], [89.3, 21.8], [89.3, 22.2],
                [88.8, 22.2], [88.8, 21.8],
            ]],
        },
        "area_ha": 98000.0,
        "health_score": 44,
        "status": "critical",
    },
    {
        "name": "Assam Tropical Forest",
        "description": "Rich tropical rainforest in northeast India, part of Indo-Burma biodiversity hotspot.",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [92.5, 26.5], [93.1, 26.5], [93.1, 27.0],
                [92.5, 27.0], [92.5, 26.5],
            ]],
        },
        "area_ha": 31200.0,
        "health_score": 78,
        "status": "healthy",
    },
]

ALERT_TEMPLATES = [
    {
        "severity": "critical",
        "ndvi_delta": -0.38,
        "ndvi_before": 0.72,
        "ndvi_after": 0.34,
        "evi_before": 0.61,
        "evi_after": 0.27,
        "confidence": 0.94,
        "change_area_ha": 1240.0,
        "days_ago": 2,
    },
    {
        "severity": "high",
        "ndvi_delta": -0.27,
        "ndvi_before": 0.68,
        "ndvi_after": 0.41,
        "evi_before": 0.57,
        "evi_after": 0.31,
        "confidence": 0.87,
        "change_area_ha": 680.0,
        "days_ago": 5,
    },
    {
        "severity": "medium",
        "ndvi_delta": -0.19,
        "ndvi_before": 0.65,
        "ndvi_after": 0.46,
        "evi_before": 0.54,
        "evi_after": 0.38,
        "confidence": 0.76,
        "change_area_ha": 320.0,
        "days_ago": 9,
    },
    {
        "severity": "low",
        "ndvi_delta": -0.16,
        "ndvi_before": 0.60,
        "ndvi_after": 0.44,
        "evi_before": 0.50,
        "evi_after": 0.35,
        "confidence": 0.71,
        "change_area_ha": 95.0,
        "days_ago": 14,
    },
    {
        "severity": "high",
        "ndvi_delta": -0.29,
        "ndvi_before": 0.71,
        "ndvi_after": 0.42,
        "evi_before": 0.60,
        "evi_after": 0.32,
        "confidence": 0.89,
        "change_area_ha": 520.0,
        "days_ago": 18,
    },
    {
        "severity": "critical",
        "ndvi_delta": -0.41,
        "ndvi_before": 0.74,
        "ndvi_after": 0.33,
        "evi_before": 0.63,
        "evi_after": 0.24,
        "confidence": 0.96,
        "change_area_ha": 1890.0,
        "days_ago": 22,
    },
]


def _make_ndvi_series(zone_id: str, days: int = 60) -> list:
    """Generate a realistic NDVI time-series with a gradual decline."""
    now = datetime.utcnow()
    snapshots = []
    ndvi = 0.72 + random.uniform(-0.04, 0.04)
    evi = ndvi * 0.83

    for i in range(days, 0, -2):
        # Slight daily noise with a gradual downward trend
        ndvi_delta = random.uniform(-0.012, 0.008) - 0.001
        ndvi = max(0.25, min(0.90, ndvi + ndvi_delta))
        evi = ndvi * (0.82 + random.uniform(-0.02, 0.02))
        cloud = random.uniform(0, 0.25)

        snapshots.append({
            "timestamp": now - timedelta(days=i),
            "zone_id": zone_id,
            "ndvi_mean": round(ndvi, 4),
            "ndvi_min": round(ndvi - random.uniform(0.05, 0.12), 4),
            "ndvi_max": round(ndvi + random.uniform(0.05, 0.10), 4),
            "evi_mean": round(evi, 4),
            "cloud_cover_pct": round(cloud * 100, 1),
            "image_url": f"https://demo.r2.dev/ndvi/{zone_id}/snap_{i}.png",
            "scan_id": f"demo_{zone_id[:6]}_{i}",
        })

    return snapshots


@router.post("/seed", response_model=dict)
async def seed_demo_data():
    """
    Populate MongoDB with demo zones, NDVI snapshots, and alerts.
    Safe to call multiple times — clears existing demo data first.
    """
    db = get_db()
    now = datetime.utcnow()

    # ── Clear existing demo data ──────────────────────────────────────────
    await db["zones"].delete_many({"description": {"$regex": "demo_seed"}})

    total_zones = 0
    total_snapshots = 0
    total_alerts = 0

    zone_ids = []

    # ── Insert zones ──────────────────────────────────────────────────────
    for zone_template in ZONES:
        zone_doc = {
            **zone_template,
            "ndvi_drop_threshold": 0.15,
            "confidence_threshold": 0.70,
            "alert_emails": [],
            "webhook_url": None,
            "active": True,
            "created_at": now - timedelta(days=90),
            "last_scanned_at": now - timedelta(hours=random.randint(1, 6)),
        }
        result = await db["zones"].insert_one(zone_doc)
        zone_id = str(result.inserted_id)
        zone_ids.append((zone_id, zone_template["name"]))
        total_zones += 1

        # ── Insert NDVI snapshot time-series ─────────────────────────────
        snapshots = _make_ndvi_series(zone_id, days=60)
        if snapshots:
            await db["ndvi_snapshots"].insert_many(snapshots)
            total_snapshots += len(snapshots)

    # ── Insert alerts across the zones ───────────────────────────────────
    alert_templates_cycle = ALERT_TEMPLATES * 2  # enough for all zones
    alert_idx = 0

    for zone_id, zone_name in zone_ids:
        # Give each zone 2-3 alerts
        num_alerts = random.randint(2, 3)
        for _ in range(num_alerts):
            tpl = alert_templates_cycle[alert_idx % len(alert_templates_cycle)]
            alert_idx += 1

            detected_at = now - timedelta(days=tpl["days_ago"])
            status = "new" if tpl["days_ago"] <= 7 else (
                "acknowledged" if tpl["days_ago"] <= 15 else "resolved"
            )

            alert_doc = {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "detected_at": detected_at,
                "ndvi_before": tpl["ndvi_before"],
                "ndvi_after": tpl["ndvi_after"],
                "ndvi_delta": tpl["ndvi_delta"],
                "evi_before": tpl["evi_before"],
                "evi_after": tpl["evi_after"],
                "change_area_ha": tpl["change_area_ha"],
                "confidence": tpl["confidence"],
                "severity": tpl["severity"],
                "change_map_url": f"https://demo.r2.dev/changes/{zone_id}/demo.png",
                "status": status,
                "notified": True,
                "notified_at": detected_at + timedelta(minutes=5),
                "notes": "",
            }
            await db["alerts"].insert_one(alert_doc)
            total_alerts += 1

    logger.info(
        f"Demo seed complete: {total_zones} zones, "
        f"{total_snapshots} snapshots, {total_alerts} alerts"
    )

    return {
        "success": True,
        "data": {
            "zones_created": total_zones,
            "snapshots_created": total_snapshots,
            "alerts_created": total_alerts,
        },
        "message": (
            f"✅ Demo seeded: {total_zones} forest zones, "
            f"{total_snapshots} NDVI snapshots, {total_alerts} alerts. "
            f"Refresh the dashboard!"
        ),
    }


@router.delete("/clear", response_model=dict)
async def clear_demo_data():
    """Remove all data from the demo collections (full reset)."""
    db = get_db()
    z = await db["zones"].delete_many({})
    a = await db["alerts"].delete_many({})
    # ndvi_snapshots is a timeseries collection — drop and recreate
    try:
        await db.drop_collection("ndvi_snapshots")
        await db.create_collection(
            "ndvi_snapshots",
            timeseries={"timeField": "timestamp", "metaField": "zone_id", "granularity": "hours"},
        )
    except Exception:
        pass

    return {
        "success": True,
        "data": {"zones_deleted": z.deleted_count, "alerts_deleted": a.deleted_count},
        "message": "All demo data cleared.",
    }
