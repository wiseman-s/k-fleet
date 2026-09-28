from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class VehicleStatusOut(BaseModel):
    vehicle_id: int
    registration_number: str
    make: Optional[str] = None
    model: Optional[str] = None
    home_station: Optional[str] = None
    status: str  # parked, on_journey, overdue
    journey_code: Optional[str] = None
    driver_name: Optional[str] = None
    destination: Optional[str] = None
    expected_return: Optional[datetime] = None


class DashboardSummaryOut(BaseModel):
    vehicles_total: int
    vehicles_parked: int
    vehicles_on_journey: int
    vehicles_overdue: int
    journeys_pending_approval: int
    journeys_approved: int
    journeys_out: int
    journeys_closed_today: int
    vehicles: List[VehicleStatusOut]