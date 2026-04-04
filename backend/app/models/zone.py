from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            try:
                ObjectId(v)
                return v
            except Exception:
                raise ValueError(f"Invalid ObjectId: {v}")
        raise ValueError(f"Cannot convert {type(v)} to ObjectId")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.to_string_ser_schema(),
        )


class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]


class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    geojson: GeoJSONPolygon
    ndvi_drop_threshold: float = Field(default=0.15, ge=0.05, le=0.40)
    confidence_threshold: float = Field(default=0.70, ge=0.10, le=1.00)
    alert_emails: List[str] = Field(default_factory=list)
    webhook_url: Optional[str] = None


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    ndvi_drop_threshold: Optional[float] = Field(None, ge=0.05, le=0.40)
    confidence_threshold: Optional[float] = Field(None, ge=0.10, le=1.00)
    alert_emails: Optional[List[str]] = None
    webhook_url: Optional[str] = None
    active: Optional[bool] = None


class ZoneResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str
    geojson: GeoJSONPolygon
    area_ha: float
    ndvi_drop_threshold: float
    confidence_threshold: float
    alert_emails: List[str]
    webhook_url: Optional[str]
    health_score: int
    status: str
    active: bool
    created_at: datetime
    last_scanned_at: Optional[datetime]

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
