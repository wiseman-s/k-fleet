from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, nullable=False)
    # types: unauthorized_attempt, overdue, geofence_violation,
    #        odometer_anomaly, gps_unavailable, unclosed_journey

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=True)
    severity = Column(String, default="medium")  # low, medium, high, critical
    message = Column(Text, nullable=False)
    location = Column(String, nullable=True)
    reported_by_name = Column(String, nullable=True)
    reported_by_staff_number = Column(String, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_by_name = Column(String, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vehicle = relationship("Vehicle")
    journey = relationship("Journey")