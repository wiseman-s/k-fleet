from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func
from app.core.database import Base


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    code = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True)

    # Geofence — center point and radius in meters.
    # If set, K-FLEET uses these to detect vehicles leaving the station zone.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_meters = Column(Float, nullable=True, default=3000.0)  # 3 km default

    created_at = Column(DateTime(timezone=True), server_default=func.now())