from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NDVISnapshotResponse(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime
    zone_id: str
    ndvi_mean: float
    ndvi_min: float
    ndvi_max: float
    evi_mean: float
    cloud_cover_pct: float
    image_url: str
    raw_tile_url: Optional[str]
    scan_id: str

    class Config:
        populate_by_name = True


class NDVISnapshotCreate(BaseModel):
    timestamp: datetime
    zone_id: str
    ndvi_mean: float
    ndvi_min: float
    ndvi_max: float
    evi_mean: float
    cloud_cover_pct: float
    image_url: str
    raw_tile_url: Optional[str] = None
    scan_id: str
