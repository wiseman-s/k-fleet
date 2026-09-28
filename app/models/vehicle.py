from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    registration_number = Column(String, unique=True, index=True, nullable=False)
    make = Column(String, nullable=True)
    model = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    home_station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    status = Column(String, default="active")  # active, maintenance, retired
    current_odometer = Column(Integer, default=0)
    fuel_type = Column(String, nullable=True)  # Petrol, Diesel
    insurance_expiry = Column(Date, nullable=True)
    inspection_expiry = Column(Date, nullable=True)
    road_license_expiry = Column(Date, nullable=True)
    qr_code = Column(String, unique=True, nullable=True)

    # Traccar GPS device ID
    traccar_device_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    home_station = relationship("Station")