from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    staff_number = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin, fleet_officer, supervisor, gatekeeper, driver
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    gate_id = Column(Integer, ForeignKey("gates.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    station = relationship("Station")
    driver = relationship("Driver")
    gate = relationship("Gate")
