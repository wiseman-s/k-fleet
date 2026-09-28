from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.station import StationOut
from app.schemas.department import DepartmentOut


class JourneyBase(BaseModel):
    vehicle_id: int
    driver_id: int
    requesting_department_id: int
    requested_by_name: str
    requested_by_staff_number: Optional[str] = None
    origin_station_id: int
    destination: str
    destination_station_id: Optional[int] = None
    purpose: str
    priority: Optional[str] = "normal"
    expected_departure: datetime
    expected_return: datetime


class JourneyCreate(JourneyBase):
    pass


class JourneyUpdate(BaseModel):
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None
    requesting_department_id: Optional[int] = None
    requested_by_name: Optional[str] = None
    requested_by_staff_number: Optional[str] = None
    origin_station_id: Optional[int] = None
    destination: Optional[str] = None
    destination_station_id: Optional[int] = None
    purpose: Optional[str] = None
    priority: Optional[str] = None
    expected_departure: Optional[datetime] = None
    expected_return: Optional[datetime] = None
    remarks: Optional[str] = None


class JourneyApprove(BaseModel):
    approved_by_id: int
    remarks: Optional[str] = None


class JourneyReject(BaseModel):
    approved_by_id: int
    rejection_reason: str


class JourneyExit(BaseModel):
    starting_odometer: int
    remarks: Optional[str] = None


class JourneyReturn(BaseModel):
    ending_odometer: int
    remarks: Optional[str] = None


class JourneyOut(JourneyBase):
    id: int
    journey_code: str
    status: str
    actual_departure: Optional[datetime] = None
    actual_return: Optional[datetime] = None
    starting_odometer: Optional[int] = None
    ending_odometer: Optional[int] = None
    distance_km: Optional[int] = None
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    origin_station: Optional[StationOut] = None
    destination_station: Optional[StationOut] = None
    requesting_department: Optional[DepartmentOut] = None

    class Config:
        from_attributes = True