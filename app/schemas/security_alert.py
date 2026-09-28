from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SecurityAlertOut(BaseModel):
    id: int
    alert_type: str
    vehicle_id: Optional[int] = None
    journey_id: Optional[int] = None
    severity: str
    message: str
    location: Optional[str] = None
    reported_by_name: Optional[str] = None
    reported_by_staff_number: Optional[str] = None
    resolved: bool
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
