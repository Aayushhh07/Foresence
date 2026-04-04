"""
Scheduled job definitions.
Runs the full satellite → NDVI → change detection → alert pipeline
for each active zone, sequentially.
"""
import logging
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from bson import ObjectId

from app.core.database import get_db
from app.core.redis_client import acquire_zone_lock, release_zone_lock
from app.services.sentinel_service import fetch_sentinel_bands
from app.services.ndvi_service import compute_ndvi_for_zone
from app.services.change_detection import detect_change
from app.services.alert_service import create_alert_if_triggered
from app.api.websocket import broadcast

logger = logging.getLogger(__name__)


async def scan_single_zone(zone_id: str) -> None:
    """
    Run the full satellite scan pipeline for one zone.
    Step 1: Fetch Sentinel-2 bands
    Step 2: Compute NDVI + EVI
    Step 3: Store snapshot
    Step 4: Detect change vs previous snapshot
    Step 5: Create alert if triggered
    """
    db = get_db()
    scan_id = str(uuid.uuid4())[:8]

    try:
        oid = ObjectId(zone_id)
    except Exception:
        logger.error(f"Invalid zone_id: {zone_id}")
        return

    zone = await db["zones"].find_one({"_id": oid})
    if not zone:
        logger.error(f"Zone not found: {zone_id}")
        return

    zone_name = zone.get("name", zone_id)
    logger.info(f"[{scan_id}] Starting scan for zone: {zone_name}")

    # Acquire distributed lock to prevent duplicate scans
    lock_acquired = await acquire_zone_lock(zone_id)
    if not lock_acquired:
        logger.info(f"[{scan_id}] Zone {zone_name} is already being scanned. Skipping.")
        return

    band_paths = None
    try:
        # --- Step 1: Fetch satellite bands ---
        geojson_coords = zone["geojson"]["coordinates"]
        band_paths = await fetch_sentinel_bands(geojson_coords, zone_id)

        if band_paths is None:
            logger.warning(f"[{scan_id}] No satellite data available for zone {zone_name}")
            await db["zones"].update_one(
                {"_id": oid},
                {"$set": {"last_scanned_at": datetime.utcnow()}},
            )
            return

        # --- Step 2: Compute NDVI + EVI ---
        geojson_polygon = zone["geojson"]
        ndvi_result = await compute_ndvi_for_zone(
            band_paths=band_paths,
            geojson_polygon=geojson_polygon,
            zone_id=zone_id,
            scan_id=scan_id,
        )

        if ndvi_result is None:
            logger.error(f"[{scan_id}] NDVI computation failed for zone {zone_name}")
            return

        # --- Step 3: Store snapshot in MongoDB ---
        snapshot_doc = {
            "timestamp": datetime.utcnow(),
            "zone_id": zone_id,
            "ndvi_mean": ndvi_result["ndvi_mean"],
            "ndvi_min": ndvi_result["ndvi_min"],
            "ndvi_max": ndvi_result["ndvi_max"],
            "evi_mean": ndvi_result["evi_mean"],
            "cloud_cover_pct": ndvi_result["cloud_cover_pct"],
            "image_url": ndvi_result["image_url"],
            "raw_tile_url": None,
            "scan_id": scan_id,
        }
        await db["ndvi_snapshots"].insert_one(snapshot_doc)
        logger.info(
            f"[{scan_id}] Snapshot stored for zone {zone_name}: "
            f"NDVI={ndvi_result['ndvi_mean']:.3f}"
        )

        # Update last_scanned_at
        await db["zones"].update_one(
            {"_id": oid},
            {"$set": {"last_scanned_at": datetime.utcnow()}},
        )

        # --- Step 4: Fetch previous snapshot for change detection ---
        prev_snapshot = await db["ndvi_snapshots"].find_one(
            {"zone_id": zone_id, "scan_id": {"$ne": scan_id}},
            sort=[("timestamp", -1)],
        )

        change_result = await detect_change(
            current_result=ndvi_result,
            previous_snapshot=prev_snapshot,
            geojson_coords=geojson_coords,
            zone_id=zone_id,
            scan_id=scan_id,
            ndvi_threshold=zone.get("ndvi_drop_threshold", 0.15),
        )

        # --- Step 5: Create alert if thresholds exceeded ---
        if change_result is not None:
            alert = await create_alert_if_triggered(
                zone=zone,
                change_result=change_result,
                websocket_broadcast_fn=broadcast,
            )
            if alert:
                logger.info(
                    f"[{scan_id}] Alert created for zone {zone_name}: "
                    f"severity={alert['severity']}"
                )

        # Broadcast scan completion heartbeat
        await broadcast({
            "type": "scan_complete",
            "zone_id": zone_id,
            "zone_name": zone_name,
            "scan_id": scan_id,
            "ndvi_mean": ndvi_result["ndvi_mean"],
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(f"[{scan_id}] Scan complete for zone: {zone_name}")

    except Exception as e:
        logger.error(
            f"[{scan_id}] Scan pipeline error for zone {zone_name}: {e}",
            exc_info=True,
        )
    finally:
        # Release the distributed lock
        await release_zone_lock(zone_id)

        # Clean up temporary raster files
        if band_paths:
            for band_path in band_paths.values():
                try:
                    parent = band_path.parent
                    shutil.rmtree(parent, ignore_errors=True)
                    break
                except Exception:
                    pass


async def run_all_zone_scans() -> None:
    """
    Scheduled job: scan all active zones sequentially.
    Process zones one at a time to avoid memory issues with large rasters.
    """
    db = get_db()
    logger.info("=== Starting scheduled zone scan run ===")

    active_zones = []
    async for zone in db["zones"].find({"active": True}):
        active_zones.append(zone)

    if not active_zones:
        logger.info("No active zones to scan.")
        return

    logger.info(f"Scanning {len(active_zones)} active zones sequentially...")

    for i, zone in enumerate(active_zones, 1):
        zone_id = str(zone["_id"])
        logger.info(f"Zone {i}/{len(active_zones)}: {zone['name']}")
        await scan_single_zone(zone_id)

    logger.info("=== Zone scan run complete ===")
