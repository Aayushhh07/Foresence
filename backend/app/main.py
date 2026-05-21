"""
FastAPI application entry point.
Reloaded to fetch new Copernicus credentials.
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_db, close_db
from app.core.redis_client import connect_redis, close_redis
from app.api.routes import zones, alerts, snapshots, health, demo
from app.api.websocket import router as ws_router
from app.scheduler.scheduler import start_scheduler, stop_scheduler

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def seed_predefined_zones():
    """Seed predefined backend-managed zones and trigger historical scanning when needed."""
    from app.core.database import get_db
    from app.scheduler.jobs import seed_historical_zone_data
    from app.api.routes.zones import _compute_area_ha

    db = get_db()

    predefined_zones = settings.predefined_zones
    if not predefined_zones:
        logger.info("No predefined zones configured; skipping startup seed.")
        return

    for zone_cfg in predefined_zones:
        name = zone_cfg.get("name")
        coordinates = zone_cfg.get("coordinates")
        if not name or not coordinates:
            logger.warning("Skipping invalid predefined zone config: missing name/coordinates.")
            continue

        existing = await db["zones"].find_one({"name": name})
        if not existing:
            geojson_polygon = {"type": "Polygon", "coordinates": coordinates}
            area_ha = _compute_area_ha(geojson_polygon["coordinates"])
            zone_doc = {
                "name": name,
                "description": zone_cfg.get("description", "Backend managed monitoring zone"),
                "geojson": geojson_polygon,
                "area_ha": area_ha,
                "ndvi_drop_threshold": zone_cfg.get("ndvi_drop_threshold", 0.15),
                "confidence_threshold": zone_cfg.get("confidence_threshold", 0.70),
                "alert_emails": zone_cfg.get("alert_emails", []),
                "webhook_url": zone_cfg.get("webhook_url"),
                "health_score": 100,
                "status": "healthy",
                "active": True,
                "created_at": datetime.utcnow(),
                "last_scanned_at": None,
            }
            result = await db["zones"].insert_one(zone_doc)
            zone_id = str(result.inserted_id)
            logger.info(f"Seeded predefined zone '{name}' ({zone_id}). Starting baseline scan.")
            asyncio.create_task(seed_historical_zone_data(zone_id))
            continue

        has_snapshots = await db["ndvi_snapshots"].find_one({"zone_id": str(existing["_id"])})
        if not has_snapshots:
            logger.info(
                f"Predefined zone '{name}' exists without snapshots. Starting baseline scan."
            )
            asyncio.create_task(seed_historical_zone_data(str(existing["_id"])))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # ── Startup ──
    logger.info("Foresence backend starting up...")

    await connect_db()
    await connect_redis()

    # Seed backend-managed predefined zones (no user polygon selection required).
    if settings.enable_predefined_zones:
        await seed_predefined_zones()
    elif settings.enable_startup_seed or settings.app_mode == "demo":
        await seed_predefined_zones()

    # Start scheduler
    start_scheduler(scan_interval_hours=settings.scan_interval_hours)

    # Schedule initial scan after 30 seconds (to populate data on first run)
    from app.scheduler.scheduler import get_scheduler
    from app.scheduler.jobs import run_all_zone_scans

    scheduler = get_scheduler()
    scheduler.add_job(
        run_all_zone_scans,
        trigger="date",
        run_date=datetime.utcnow() + timedelta(seconds=30),
        id="initial_scan",
        replace_existing=True,
        name="Initial Zone Scan (30s delay)",
    )

    logger.info("Foresence backend ready.")
    yield

    # ── Shutdown ──
    logger.info("Foresence backend shutting down...")
    stop_scheduler()
    await close_db()
    await close_redis()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Foresence API",
    description="Production-grade deforestation monitoring using Sentinel-2 satellite imagery",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(zones.router)
app.include_router(alerts.router)
app.include_router(snapshots.router)
app.include_router(health.router)
if settings.enable_demo_routes or settings.app_mode == "demo":
    app.include_router(demo.router)
app.include_router(ws_router)

# Serve local static files
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

static_dir = Path(__file__).resolve().parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")



@app.get("/")
async def root():
    return {
        "success": True,
        "data": {"name": "Foresence API", "version": "1.0.0"},
        "message": "Foresence deforestation monitoring API is running",
    }
