from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    staff_number = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    employment_type = Column(String, default="permanent")  # permanent, contract
    duty_station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    license_number = Column(String, nullable=True)
    license_expiry = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    is_supervisor = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    duty_station = relationship("Station")