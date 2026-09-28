from pydantic import BaseModel
from typing import Optional


class StationBase(BaseModel):
    name: str
    code: Optional[str] = None
    is_active: Optional[bool] = True
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: Optional[float] = 3000.0


class StationCreate(StationBase):
    pass


class StationOut(StationBase):
    id: int

    class Config:
        from_attributes = True