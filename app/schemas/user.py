from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.schemas.station import StationOut


class UserBase(BaseModel):
    staff_number: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    station_id: Optional[int] = None
    driver_id: Optional[int] = None
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    station_id: Optional[int] = None
    driver_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: int
    created_at: datetime
    station: Optional[StationOut] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    staff_number: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut