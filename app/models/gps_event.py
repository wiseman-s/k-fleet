from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class GpsEvent(Base):
    __tablename__ = "gps_events"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=True, index=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)          # km/h
    course = Column(Float, nullable=True)         # direction in degrees
    accuracy = Column(Float, nullable=True)       # meters

    device_time = Column(DateTime(timezone=True), nullable=True)   # when the phone/tracker got the fix
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())  # when we stored it in K-FLEET

    vehicle = relationship("Vehicle")
    journey = relationship("Journey")