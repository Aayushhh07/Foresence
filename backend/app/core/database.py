import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING, GEOSPHERE
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient = None
_db: AsyncIOMotorDatabase = None


async def connect_db() -> None:
    """Connect to MongoDB and create required indexes."""
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.db_name]

    # Ping to verify connection
    await _client.admin.command("ping")
    logger.info("Connected to MongoDB successfully.")

    # Create indexes
    await _create_indexes()


async def _create_indexes() -> None:
    """Create all required MongoDB indexes."""
    # Zones collection
    zones_col = _db["zones"]
    await zones_col.create_indexes([
        IndexModel([("status", ASCENDING)]),
        IndexModel([("active", ASCENDING)]),
        IndexModel([("geojson", GEOSPHERE)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # Alerts collection
    alerts_col = _db["alerts"]
    await alerts_col.create_indexes([
        IndexModel([("zone_id", ASCENDING)]),
        IndexModel([("detected_at", DESCENDING)]),
        IndexModel([("severity", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("confidence", DESCENDING)]),
    ])

    # NDVI snapshots collection (timeseries)
    snapshot_names = await _db.list_collection_names()
    if "ndvi_snapshots" not in snapshot_names:
        await _db.create_collection(
            "ndvi_snapshots",
            timeseries={
                "timeField": "timestamp",
                "metaField": "zone_id",
                "granularity": "hours",
            },
        )
        logger.info("Created timeseries collection: ndvi_snapshots")

    ndvi_col = _db["ndvi_snapshots"]
    await ndvi_col.create_indexes([
        IndexModel([("zone_id", ASCENDING), ("timestamp", DESCENDING)]),
    ])

    logger.info("MongoDB indexes created successfully.")


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _db
