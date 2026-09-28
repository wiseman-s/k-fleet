from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.schemas.station import StationOut


class DriverBase(BaseModel):
    staff_number: str
    full_name: str
    phone: Optional[str] = None
    employment_type: Optional[str] = "permanent"
    duty_station_id: int
    license_number: Optional[str] = None
    license_expiry: Optional[date] = None
    is_active: Optional[bool] = True
    is_supervisor: Optional[bool] = False


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    employment_type: Optional[str] = None
    duty_station_id: Optional[int] = None
    license_number: Optional[str] = None
    license_expiry: Optional[date] = None
    is_active: Optional[bool] = None
    is_supervisor: Optional[bool] = None


class DriverOut(DriverBase):
    id: int
    duty_station: Optional[StationOut] = None

    class Config:
        from_attributes = True