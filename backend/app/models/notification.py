from typing import List, Optional
from pydantic import BaseModel, Field


class ZoneReportRequest(BaseModel):
    zone_ids: List[str] = Field(..., min_length=1)
    recipients: Optional[List[str]] = None
