from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.schemas.station import StationOut


class VehicleBase(BaseModel):
    registration_number: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    home_station_id: int
    status: Optional[str] = "active"
    current_odometer: Optional[int] = 0
    fuel_type: Optional[str] = None
    insurance_expiry: Optional[date] = None
    inspection_expiry: Optional[date] = None
    road_license_expiry: Optional[date] = None
    qr_code: Optional[str] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    home_station_id: Optional[int] = None
    status: Optional[str] = None
    current_odometer: Optional[int] = None
    fuel_type: Optional[str] = None
    insurance_expiry: Optional[date] = None
    inspection_expiry: Optional[date] = None
    road_license_expiry: Optional[date] = None
    qr_code: Optional[str] = None


class VehicleOut(VehicleBase):
    id: int
    home_station: Optional[StationOut] = None

    class Config:
        from_attributes = True