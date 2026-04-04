from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AlertResponse(BaseModel):
    id: str = Field(alias="_id")
    zone_id: str
    zone_name: str
    detected_at: datetime
    ndvi_before: float
    ndvi_after: float
    ndvi_delta: float
    evi_before: float
    evi_after: float
    change_area_ha: float
    confidence: float
    severity: str
    change_map_url: str
    status: str
    notified: bool
    notified_at: Optional[datetime]
    notes: str

    class Config:
        populate_by_name = True


class AlertStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(acknowledged|resolved)$")
    notes: Optional[str] = None


class AlertCreate(BaseModel):
    zone_id: str
    zone_name: str
    detected_at: datetime
    ndvi_before: float
    ndvi_after: float
    ndvi_delta: float
    evi_before: float
    evi_after: float
    change_area_ha: float
    confidence: float
    severity: str
    change_map_url: str
    status: str = "new"
    notified: bool = False
    notified_at: Optional[datetime] = None
    notes: str = ""
