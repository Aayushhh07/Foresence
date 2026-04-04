"""
FastAPI application entry point.
"""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_db, close_db
from app.core.redis_client import connect_redis, close_redis
from app.api.routes import zones, alerts, snapshots, health
from app.api.websocket import router as ws_router
from app.scheduler.scheduler import start_scheduler, stop_scheduler

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # ── Startup ──
    logger.info("Foresence backend starting up...")

    await connect_db()
    await connect_redis()

    # Start scheduler
    start_scheduler(scan_interval_hours=settings.scan_interval_hours)

    # Schedule initial scan after 30 seconds (to populate data on first run)
    from app.scheduler.scheduler import get_scheduler
    from app.scheduler.jobs import run_all_zone_scans

    scheduler = get_scheduler()
    scheduler.add_job(
        run_all_zone_scans,
        trigger="date",
        run_date=asyncio.get_event_loop().time() + 30,
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
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "success": True,
        "data": {"name": "Foresence API", "version": "1.0.0"},
        "message": "Foresence deforestation monitoring API is running",
    }
