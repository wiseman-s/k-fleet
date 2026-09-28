from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Journey(Base):
    __tablename__ = "journeys"

    id = Column(Integer, primary_key=True, index=True)
    journey_code = Column(String, unique=True, index=True, nullable=False)

    # Assignment
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)

    # Requesting side
    requesting_department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    requested_by_name = Column(String, nullable=False)
    requested_by_staff_number = Column(String, nullable=True)

    # Route
    origin_station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    destination = Column(String, nullable=False)  # free text
    destination_station_id = Column(Integer, ForeignKey("stations.id"), nullable=True)

    # Purpose and priority
    purpose = Column(Text, nullable=False)
    priority = Column(String, default="normal")  # normal, urgent

    # Times
    expected_departure = Column(DateTime(timezone=True), nullable=False)
    expected_return = Column(DateTime(timezone=True), nullable=False)
    actual_departure = Column(DateTime(timezone=True), nullable=True)
    actual_return = Column(DateTime(timezone=True), nullable=True)

    # Odometer
    starting_odometer = Column(Integer, nullable=True)
    ending_odometer = Column(Integer, nullable=True)
    distance_km = Column(Integer, nullable=True)

    # Lifecycle
    status = Column(String, default="pending")
    # pending, approved, rejected, out, returned, closed, overdue
    rejection_reason = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)

    # Supervisor
    approved_by_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    vehicle = relationship("Vehicle")
    driver = relationship("Driver", foreign_keys=[driver_id])
    approved_by = relationship("Driver", foreign_keys=[approved_by_id])
    requesting_department = relationship("Department")
    origin_station = relationship("Station", foreign_keys=[origin_station_id])
    destination_station = relationship("Station", foreign_keys=[destination_station_id])